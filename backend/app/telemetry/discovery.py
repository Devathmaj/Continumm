import asyncio
import datetime
import logging
import re
import xml.etree.ElementTree as ET


def parse_arp_table():
    devices = []
    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as arp_file:
            lines = arp_file.readlines()[1:]
    except Exception:
        return devices

    for line in lines:
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 6:
            continue
        ip_address, _, _, mac_address, _, _ = parts[:6]
        if mac_address == "00:00:00:00:00:00":
            continue
        devices.append(
            {
                "ip_address": ip_address,
                "mac_address": mac_address,
                "hostname": None,
                "vendor": None,
                "ports": [],
            }
        )
    return devices


async def scapy_arp_scan(subnet, logger):
    devices = []
    try:
        from scapy.all import ARP, Ether, srp
    except Exception as exc:
        logger.warning("scapy not available: %s", exc)
        return devices

    def _scan():
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=subnet)
        answered, _ = srp(packet, timeout=2, verbose=False)
        results = []
        for _, received in answered:
            results.append(
                {
                    "ip_address": received.psrc,
                    "mac_address": received.hwsrc,
                    "hostname": None,
                    "vendor": None,
                    "ports": [],
                }
            )
        return results

    try:
        devices = await asyncio.to_thread(_scan)
    except Exception as exc:
        logger.warning("scapy scan failed for %s: %s", subnet, exc)
        return []
    return devices


async def run_nmap_discovery(subnet, config, logger):
    args = [config.NMAP_PATH, "-sn", "-oX", "-", subnet]
    if config.NMAP_DISABLE_ARP_PING:
        args.extend(["--disable-arp-ping", "-PE"])
    if config.NMAP_MIN_RATE:
        args.extend(["--min-rate", config.NMAP_MIN_RATE])
    if config.NMAP_MAX_RATE:
        args.extend(["--max-rate", config.NMAP_MAX_RATE])

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning("nmap binary not found, skipping nmap discovery")
        return []

    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("nmap discovery failed for %s: %s", subnet, stderr.decode())
        return []
    return parse_nmap_hosts(stdout.decode())


async def run_nmap_ports(ip_address, config, logger):
    args = [
        config.NMAP_PATH,
        "-sV",
        "--top-ports",
        str(config.PORT_SCAN_TOP_PORTS),
        "-oX",
        "-",
        ip_address,
    ]
    if config.NMAP_MIN_RATE:
        args.extend(["--min-rate", config.NMAP_MIN_RATE])
    if config.NMAP_MAX_RATE:
        args.extend(["--max-rate", config.NMAP_MAX_RATE])

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning("nmap binary not found, skipping port scan")
        return []

    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("nmap port scan failed for %s: %s", ip_address, stderr.decode())
        return []
    return parse_nmap_ports(stdout.decode())


def parse_nmap_hosts(xml_text):
    devices = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return devices

    for host in root.findall("host"):
        status = host.find("status")
        if status is None or status.attrib.get("state") != "up":
            continue
        ip_address = None
        mac_address = None
        vendor = None
        for address in host.findall("address"):
            addr_type = address.attrib.get("addrtype")
            if addr_type == "ipv4":
                ip_address = address.attrib.get("addr")
            elif addr_type == "mac":
                mac_address = address.attrib.get("addr")
                vendor = address.attrib.get("vendor")
        hostname = None
        hostnames = host.find("hostnames")
        if hostnames is not None:
            hostname_node = hostnames.find("hostname")
            if hostname_node is not None:
                hostname = hostname_node.attrib.get("name")

        if not ip_address:
            continue
        devices.append(
            {
                "ip_address": ip_address,
                "mac_address": mac_address,
                "hostname": hostname,
                "vendor": vendor,
                "ports": [],
            }
        )
    return devices


def parse_nmap_ports(xml_text):
    ports = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ports

    host = root.find("host")
    if host is None:
        return ports

    ports_node = host.find("ports")
    if ports_node is None:
        return ports

    for port_node in ports_node.findall("port"):
        port_state = port_node.find("state")
        if port_state is None or port_state.attrib.get("state") != "open":
            continue
        service_node = port_node.find("service")
        service_name = None
        if service_node is not None:
            service_name = service_node.attrib.get("name")
        ports.append(
            {
                "port": int(port_node.attrib.get("portid", "0")),
                "protocol": port_node.attrib.get("protocol", "tcp"),
                "service": service_name,
                "state": port_state.attrib.get("state"),
            }
        )
    return ports


async def discover_subnet(subnet, config, logger):
    devices = {}
    if config.SCAN_USE_ARP:
        for device in parse_arp_table():
            devices.setdefault(device["ip_address"], device)

    if config.SCAN_USE_SCAPY:
        for device in await scapy_arp_scan(subnet, logger):
            devices.setdefault(device["ip_address"], device)

    if config.SCAN_USE_NMAP:
        for device in await run_nmap_discovery(subnet, config, logger):
            existing = devices.get(device["ip_address"], {})
            merged = {**existing, **device}
            devices[device["ip_address"]] = merged

    device_list = list(devices.values())
    if config.PORT_SCAN_ENABLED and device_list:
        await enrich_ports(device_list, config, logger)

    return device_list


async def enrich_ports(device_list, config, logger):
    semaphore = asyncio.Semaphore(config.PORT_SCAN_LIMIT)

    async def _scan(device):
        async with semaphore:
            ports = await run_nmap_ports(device["ip_address"], config, logger)
            device["ports"] = ports

    tasks = [asyncio.create_task(_scan(device)) for device in device_list]
    if tasks:
        await asyncio.gather(*tasks)
