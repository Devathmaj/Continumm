import os
import sys
import json
import logging
import signal
import subprocess
import time
from datetime import datetime
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from config import config
from db import get_session, init_db
from models import AlertEvent, Device, DevicePort, DeviceStatus, ScanRun
from telemetry.service import TelemetryService

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except Exception:
    OTEL_AVAILABLE = False

# Structured JSON logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id
        if hasattr(record, 'span_id'):
            log_data['span_id'] = record.span_id
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure structured logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger('continumm')
logger.addHandler(handler)
logger.setLevel(config.LOG_LEVEL)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'request_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'error_total',
    'Total number of errors',
    ['method', 'endpoint', 'error_type']
)

# Get git commit hash
def get_git_commit():
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return commit
    except Exception:
        # Fallback to environment variable or file
        commit = os.getenv('GIT_COMMIT', 'unknown')
        if commit == 'unknown':
            try:
                with open('/app/.git_commit', 'r') as f:
                    commit = f.read().strip()
            except Exception:
                pass
        return commit

GIT_COMMIT = get_git_commit()


def configure_tracing(flask_app):
    if not config.OTEL_ENABLED:
        return
    if not config.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning("OTEL enabled but OTEL_EXPORTER_OTLP_ENDPOINT is empty")
        return
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry packages not available")
        return

    resource = Resource.create({"service.name": config.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(flask_app)

# Middleware for request tracking
@app.before_request
def before_request():
    request.start_time = time.time()
    request.request_id = os.urandom(8).hex()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)
        
        if response.status_code >= 400:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                error_type=f"{response.status_code}"
            ).inc()
        
        # Log request
        log_entry = logger.makeRecord(
            logger.name, logging.INFO, '', 0,
            f"{request.method} {request.path} {response.status_code}",
            (), None
        )
        log_entry.request_id = getattr(request, 'request_id', 'unknown')
        log_entry.path = request.path
        log_entry.method = request.method
        log_entry.status_code = response.status_code
        log_entry.duration = round(duration, 4)
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            span_ctx = span.get_span_context()
            if span_ctx and span_ctx.trace_id:
                log_entry.trace_id = format(span_ctx.trace_id, '032x')
                log_entry.span_id = format(span_ctx.span_id, '016x')
        logger.handle(log_entry)
    
    return response

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint - returns 200 only if all dependencies are healthy
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {}
    }
    
    all_healthy = True
    
    health_status['checks']['application'] = 'healthy'

    if config.DATABASE_URL:
        try:
            init_db()
            health_status['checks']['database'] = 'healthy'
        except Exception:
            health_status['checks']['database'] = 'unhealthy'
            all_healthy = False
    else:
        health_status['checks']['database'] = 'not_configured'

    health_status['checks']['telemetry'] = 'enabled' if telemetry_service.running else 'disabled'
    
    if not all_healthy:
        health_status['status'] = 'unhealthy'
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200

# Metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus metrics endpoint
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Version endpoint
@app.route('/version', methods=['GET'])
def version():
    """
    Returns version information including git commit hash
    """
    return jsonify({
        'version': GIT_COMMIT,
        'commit': GIT_COMMIT,
        'environment': config.ENVIRONMENT,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route('/')
def hello():
    return jsonify({
        'service': 'Continumm Backend',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'metrics': '/metrics',
            'version': '/version'
        }
    })


def _db_unavailable():
    return jsonify({'error': 'database_unavailable'}), 503


@app.route('/api/devices', methods=['GET'])
def list_devices():
    limit = int(request.args.get('limit', '200'))
    devices_payload = []
    try:
        with get_session() as session:
            devices = session.query(Device).order_by(Device.last_seen.desc()).limit(limit).all()
            for device in devices:
                status = (
                    session.query(DeviceStatus)
                    .filter(DeviceStatus.device_id == device.id)
                    .order_by(DeviceStatus.observed_at.desc())
                    .first()
                )
                ports = (
                    session.query(DevicePort)
                    .filter(DevicePort.device_id == device.id)
                    .order_by(DevicePort.port.asc())
                    .all()
                )
                devices_payload.append(
                    {
                        'id': device.id,
                        'ip_address': device.ip_address,
                        'mac_address': device.mac_address,
                        'hostname': device.hostname,
                        'vendor': device.vendor,
                        'first_seen': device.first_seen.isoformat() + 'Z',
                        'last_seen': device.last_seen.isoformat() + 'Z',
                        'status': _serialize_status(status),
                        'ports': [
                            {
                                'port': port.port,
                                'protocol': port.protocol,
                                'service': port.service,
                                'state': port.state,
                                'last_seen': port.last_seen.isoformat() + 'Z',
                            }
                            for port in ports
                        ],
                    }
                )
    except Exception:
        return _db_unavailable()
    return jsonify({'devices': devices_payload})


@app.route('/api/devices/<int:device_id>', methods=['GET'])
def get_device(device_id):
    try:
        with get_session() as session:
            device = session.query(Device).filter(Device.id == device_id).first()
            if device is None:
                return jsonify({'error': 'not_found'}), 404
            status = (
                session.query(DeviceStatus)
                .filter(DeviceStatus.device_id == device.id)
                .order_by(DeviceStatus.observed_at.desc())
                .first()
            )
            ports = (
                session.query(DevicePort)
                .filter(DevicePort.device_id == device.id)
                .order_by(DevicePort.port.asc())
                .all()
            )
    except Exception:
        return _db_unavailable()

    payload = {
        'id': device.id,
        'ip_address': device.ip_address,
        'mac_address': device.mac_address,
        'hostname': device.hostname,
        'vendor': device.vendor,
        'first_seen': device.first_seen.isoformat() + 'Z',
        'last_seen': device.last_seen.isoformat() + 'Z',
        'status': _serialize_status(status),
        'ports': [
            {
                'port': port.port,
                'protocol': port.protocol,
                'service': port.service,
                'state': port.state,
                'last_seen': port.last_seen.isoformat() + 'Z',
            }
            for port in ports
        ],
    }
    return jsonify(payload)


@app.route('/api/devices/<int:device_id>/metrics', methods=['GET'])
def get_device_metrics(device_id):
    limit = int(request.args.get('limit', '100'))
    try:
        with get_session() as session:
            status_rows = (
                session.query(DeviceStatus)
                .filter(DeviceStatus.device_id == device_id)
                .order_by(DeviceStatus.observed_at.desc())
                .limit(limit)
                .all()
            )
    except Exception:
        return _db_unavailable()
    metrics_payload = [
        {
            'observed_at': row.observed_at.isoformat() + 'Z',
            'online': row.online,
            'latency_ms': row.latency_ms,
            'packet_loss_percent': row.packet_loss_percent,
            'jitter_ms': row.jitter_ms,
            'response_time_ms': row.response_time_ms,
            'uptime_percent': row.uptime_percent,
        }
        for row in reversed(status_rows)
    ]
    return jsonify({'device_id': device_id, 'metrics': metrics_payload})


@app.route('/api/alerts', methods=['GET'])
def list_alerts():
    limit = int(request.args.get('limit', '100'))
    try:
        with get_session() as session:
            alerts = (
                session.query(AlertEvent)
                .order_by(AlertEvent.observed_at.desc())
                .limit(limit)
                .all()
            )
    except Exception:
        return _db_unavailable()
    payload = [
        {
            'id': alert.id,
            'device_id': alert.device_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'observed_at': alert.observed_at.isoformat() + 'Z',
            'resolved_at': alert.resolved_at.isoformat() + 'Z' if alert.resolved_at else None,
        }
        for alert in alerts
    ]
    return jsonify({'alerts': payload})


@app.route('/api/telemetry/overview', methods=['GET'])
def telemetry_overview():
    try:
        with get_session() as session:
            device_count = session.query(Device).count()
            last_scan = session.query(ScanRun).order_by(ScanRun.started_at.desc()).first()
            last_alert = session.query(AlertEvent).order_by(AlertEvent.observed_at.desc()).first()
    except Exception:
        return _db_unavailable()

    payload = {
        'device_count': device_count,
        'last_scan': _serialize_scan(last_scan),
        'last_alert': _serialize_alert(last_alert),
    }
    return jsonify(payload)

# Graceful shutdown handling
class GracefulShutdown:
    def __init__(self, telemetry):
        self._telemetry = telemetry
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        logger.info(f"Shutdown signal received: {signum}")
        self.shutdown_requested = True
        self._telemetry.stop()
        sys.exit(0)


def _serialize_status(status):
    if status is None:
        return None
    return {
        'observed_at': status.observed_at.isoformat() + 'Z',
        'online': status.online,
        'latency_ms': status.latency_ms,
        'packet_loss_percent': status.packet_loss_percent,
        'jitter_ms': status.jitter_ms,
        'response_time_ms': status.response_time_ms,
        'uptime_percent': status.uptime_percent,
    }


def _serialize_scan(scan):
    if scan is None:
        return None
    return {
        'subnet': scan.subnet,
        'started_at': scan.started_at.isoformat() + 'Z',
        'finished_at': scan.finished_at.isoformat() + 'Z' if scan.finished_at else None,
        'status': scan.status,
        'devices_found': scan.devices_found,
        'error_message': scan.error_message,
    }


def _serialize_alert(alert):
    if alert is None:
        return None
    return {
        'id': alert.id,
        'device_id': alert.device_id,
        'alert_type': alert.alert_type,
        'severity': alert.severity,
        'message': alert.message,
        'observed_at': alert.observed_at.isoformat() + 'Z',
    }


telemetry_service = TelemetryService(logger)
configure_tracing(app)
telemetry_service.start()
shutdown_handler = GracefulShutdown(telemetry_service)

if __name__ == '__main__':
    logger.info(f"Starting Continumm Backend on {config.HOST}:{config.PORT}")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info(f"Git commit: {GIT_COMMIT}")
    
    try:
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=False
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
    finally:
        logger.info("Application shutdown complete")