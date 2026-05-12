import asyncio
import threading
import time
from collections import defaultdict, deque
from datetime import datetime

from config import config
from db import get_session, init_db, try_acquire_leader_lock
from models import AlertEvent, Device, DevicePort, DeviceStatus, ScanRun
from telemetry.discovery import discover_subnet
from telemetry.metrics import (
    ALERTS_TOTAL,
    DEVICE_INFO,
    DEVICE_JITTER_MS,
    DEVICE_LATENCY_MS,
    DEVICE_ONLINE,
    DEVICE_OPEN_PORT,
    DEVICE_PACKET_LOSS_PERCENT,
    DEVICE_RESPONSE_TIME_MS,
    DEVICE_UPTIME_PERCENT,
    DISCOVERY_ACTIVE_DEVICES,
    DISCOVERY_DEVICES_FOUND,
    DISCOVERY_SCAN_DURATION,
    DISCOVERY_SCAN_FAILURES,
    POLLING_FAILURES,
    POLLING_QUEUE_DEPTH,
    POLLING_RUN_DURATION,
    WORKER_LAST_RUN_TIMESTAMP,
)
from telemetry.monitoring import ping_host


class TelemetryService:
    def __init__(self, logger):
        self._logger = logger
        self._stop_event = threading.Event()
        self._thread = None
        self._lock_conn = None
        self._running = False
        self._port_cache = defaultdict(set)
        self._uptime_cache = defaultdict(lambda: deque(maxlen=100))
        self._alert_cache = {}
        self._offline_counts = defaultdict(int)

    @property
    def running(self):
        return self._running

    def start(self):
        if not config.TELEMETRY_ENABLED:
            self._logger.info("Telemetry disabled via TELEMETRY_ENABLED")
            return
        if not config.DATABASE_URL:
            self._logger.warning("DATABASE_URL not set, telemetry disabled")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._lock_conn is not None:
            self._lock_conn.close()
            self._lock_conn = None
        self._running = False

    def _run(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        self._logger.info("Starting telemetry service")
        if not config.TELEMETRY_DISABLE_LEADER_LOCK:
            self._lock_conn = try_acquire_leader_lock()
            if self._lock_conn is None:
                self._logger.info("Telemetry leader lock not acquired, skipping worker")
                return

        if not init_db():
            self._logger.warning("Database initialization failed, telemetry disabled")
            return

        self._running = True
        discovery_task = asyncio.create_task(self._discovery_loop())
        polling_task = asyncio.create_task(self._polling_loop())

        while not self._stop_event.is_set():
            await asyncio.sleep(1)

        discovery_task.cancel()
        polling_task.cancel()
        self._running = False

    async def _discovery_loop(self):
        while not self._stop_event.is_set():
            start_time = time.perf_counter()
            for subnet in config.SCAN_SUBNETS:
                if self._stop_event.is_set():
                    break
                await self._run_discovery(subnet)
            duration = time.perf_counter() - start_time
            WORKER_LAST_RUN_TIMESTAMP.labels(worker="discovery").set(time.time())
            await asyncio.sleep(max(0, config.DISCOVERY_INTERVAL_SECONDS - duration))

    async def _run_discovery(self, subnet):
        scan_start = time.perf_counter()
        run_id = None
        with get_session() as session:
            run_record = ScanRun(
                subnet=subnet,
                started_at=datetime.utcnow(),
                status="running",
                devices_found=0,
            )
            session.add(run_record)
            session.flush()
            run_id = run_record.id

        try:
            devices = await discover_subnet(subnet, config, self._logger)
            self._persist_devices(devices)
            self._update_port_metrics(devices)
            DISCOVERY_DEVICES_FOUND.labels(subnet=subnet).set(len(devices))
            DISCOVERY_ACTIVE_DEVICES.set(self._count_devices())
            scan_duration = time.perf_counter() - scan_start
            DISCOVERY_SCAN_DURATION.labels(subnet=subnet).observe(scan_duration)

            with get_session() as session:
                run = session.query(ScanRun).filter(ScanRun.id == run_id).first()
                if run:
                    run.status = "complete"
                    run.devices_found = len(devices)
                    run.finished_at = datetime.utcnow()
        except Exception as exc:
            DISCOVERY_SCAN_FAILURES.labels(subnet=subnet).inc()
            self._logger.warning("Discovery failed for %s: %s", subnet, exc)
            with get_session() as session:
                run = session.query(ScanRun).filter(ScanRun.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.error_message = str(exc)
                    run.finished_at = datetime.utcnow()

    async def _polling_loop(self):
        while not self._stop_event.is_set():
            start_time = time.perf_counter()
            try:
                await self._run_polling()
            except Exception as exc:
                POLLING_FAILURES.inc()
                self._logger.warning("Polling loop failed: %s", exc)
            duration = time.perf_counter() - start_time
            POLLING_RUN_DURATION.observe(duration)
            WORKER_LAST_RUN_TIMESTAMP.labels(worker="polling").set(time.time())
            await asyncio.sleep(max(0, config.POLL_INTERVAL_SECONDS - duration))

    async def _run_polling(self):
        with get_session() as session:
            devices = [
                {"id": device.id, "ip_address": device.ip_address}
                for device in session.query(Device).all()
            ]
        POLLING_QUEUE_DEPTH.set(len(devices))

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_PINGS)

        async def _probe(device):
            async with semaphore:
                stats = await ping_host(device["ip_address"], config)
                self._handle_poll_result(device, stats)

        tasks = [asyncio.create_task(_probe(device)) for device in devices]
        if tasks:
            await asyncio.gather(*tasks)

    def _persist_devices(self, devices):
        now = datetime.utcnow()
        with get_session() as session:
            for device in devices:
                db_device = None
                if device.get("mac_address"):
                    db_device = (
                        session.query(Device)
                        .filter(Device.mac_address == device["mac_address"])
                        .first()
                    )
                if db_device is None:
                    db_device = (
                        session.query(Device)
                        .filter(Device.ip_address == device["ip_address"])
                        .first()
                    )
                if db_device is None:
                    db_device = Device(
                        ip_address=device["ip_address"],
                        mac_address=device.get("mac_address"),
                        hostname=device.get("hostname"),
                        vendor=device.get("vendor"),
                        first_seen=now,
                        last_seen=now,
                    )
                    session.add(db_device)
                    session.flush()
                else:
                    db_device.ip_address = device["ip_address"]
                    db_device.mac_address = device.get("mac_address")
                    db_device.hostname = device.get("hostname")
                    db_device.vendor = device.get("vendor")
                    db_device.last_seen = now

                self._persist_ports(session, db_device.id, device.get("ports", []), now)
                self._update_device_info_metric(db_device)

    def _persist_ports(self, session, device_id, ports, now):
        for port in ports:
            existing = (
                session.query(DevicePort)
                .filter(
                    DevicePort.device_id == device_id,
                    DevicePort.port == port["port"],
                    DevicePort.protocol == port.get("protocol", "tcp"),
                )
                .first()
            )
            if existing is None:
                session.add(
                    DevicePort(
                        device_id=device_id,
                        port=port["port"],
                        protocol=port.get("protocol", "tcp"),
                        service=port.get("service"),
                        state=port.get("state"),
                        last_seen=now,
                    )
                )
            else:
                existing.service = port.get("service")
                existing.state = port.get("state")
                existing.last_seen = now

    def _update_port_metrics(self, devices):
        for device in devices:
            ip_address = device["ip_address"]
            current_ports = set()
            for port in device.get("ports", []):
                service = port.get("service") or "unknown"
                key = (str(port["port"]), service)
                current_ports.add(key)
                DEVICE_OPEN_PORT.labels(ip=ip_address, port=str(port["port"]), service=service).set(1)
            removed = self._port_cache[ip_address] - current_ports
            for port, service in removed:
                DEVICE_OPEN_PORT.labels(ip=ip_address, port=port, service=service).set(0)
            self._port_cache[ip_address] = current_ports

    def _update_device_info_metric(self, device):
        hostname = self._normalize_label(device.hostname)
        mac_address = self._normalize_label(device.mac_address)
        vendor = self._normalize_label(device.vendor)
        DEVICE_INFO.labels(
            ip=device.ip_address,
            device_id=str(device.id),
            hostname=hostname,
            mac_address=mac_address,
            vendor=vendor,
        ).set(1)

    @staticmethod
    def _normalize_label(value):
        if value is None:
            return "unknown"
        value = str(value).strip()
        return value if value else "unknown"

    def _handle_poll_result(self, device, stats):
        now = datetime.utcnow()
        device_id = str(device["id"])
        ip_address = device["ip_address"]

        online = stats.get("online", False)
        latency_ms = stats.get("latency_ms")
        packet_loss = stats.get("packet_loss_percent")
        jitter_ms = stats.get("jitter_ms")
        response_time_ms = stats.get("response_time_ms")

        self._uptime_cache[device["id"]].append(1 if online else 0)
        uptime_percent = None
        if self._uptime_cache[device["id"]]:
            uptime_percent = (
                sum(self._uptime_cache[device["id"]])
                / len(self._uptime_cache[device["id"]])
                * 100
            )

        with get_session() as session:
            session.add(
                DeviceStatus(
                    device_id=device["id"],
                    observed_at=now,
                    online=online,
                    latency_ms=latency_ms,
                    packet_loss_percent=packet_loss,
                    jitter_ms=jitter_ms,
                    response_time_ms=response_time_ms,
                    uptime_percent=uptime_percent,
                )
            )

        DEVICE_ONLINE.labels(ip=ip_address, device_id=device_id).set(1 if online else 0)
        if latency_ms is not None:
            DEVICE_LATENCY_MS.labels(ip=ip_address, device_id=device_id).set(latency_ms)
        if packet_loss is not None:
            DEVICE_PACKET_LOSS_PERCENT.labels(ip=ip_address, device_id=device_id).set(packet_loss)
        if jitter_ms is not None:
            DEVICE_JITTER_MS.labels(ip=ip_address, device_id=device_id).set(jitter_ms)
        if response_time_ms is not None:
            DEVICE_RESPONSE_TIME_MS.labels(ip=ip_address, device_id=device_id).set(response_time_ms)
        if uptime_percent is not None:
            DEVICE_UPTIME_PERCENT.labels(ip=ip_address, device_id=device_id).set(uptime_percent)

        self._evaluate_alerts(device, online, latency_ms, packet_loss)

    def _evaluate_alerts(self, device, online, latency_ms, packet_loss):
        now = datetime.utcnow()
        device_id = device["id"]

        if online:
            self._offline_counts[device_id] = 0
        else:
            self._offline_counts[device_id] += 1

        if self._offline_counts[device_id] >= config.ALERT_OFFLINE_AFTER:
            self._emit_alert(device, "device_offline", "critical", "Device appears offline")

        if latency_ms is not None and latency_ms >= config.ALERT_LATENCY_MS:
            self._emit_alert(device, "latency_spike", "warning", f"Latency {latency_ms:.1f}ms")

        if packet_loss is not None and packet_loss >= config.ALERT_PACKET_LOSS_PERCENT:
            self._emit_alert(
                device,
                "packet_loss",
                "warning",
                f"Packet loss {packet_loss:.1f}%",
            )

    def _emit_alert(self, device, alert_type, severity, message):
        key = (device["id"], alert_type)
        last_seen = self._alert_cache.get(key)
        now_ts = time.time()
        if last_seen and now_ts - last_seen < config.ALERT_COOLDOWN_SECONDS:
            return
        self._alert_cache[key] = now_ts

        with get_session() as session:
            session.add(
                AlertEvent(
                    device_id=device["id"],
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    observed_at=datetime.utcnow(),
                )
            )

        ALERTS_TOTAL.labels(alert_type=alert_type, severity=severity).inc()

    def _count_devices(self):
        with get_session() as session:
            return session.query(Device).count()
