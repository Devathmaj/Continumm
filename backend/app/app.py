import os
import sys
import json
import logging
import signal
import subprocess
from datetime import datetime
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
import time

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
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure structured logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger('continumm')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Configuration from environment variables only
class Config:
    PORT = int(os.getenv('PORT', '8000'))
    HOST = os.getenv('HOST', '0.0.0.0')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

config = Config()
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
    
    # Add dependency health checks here
    # Example: Database check
    # try:
    #     # Check database connection
    #     health_status['checks']['database'] = 'healthy'
    # except Exception as e:
    #     health_status['checks']['database'] = 'unhealthy'
    #     all_healthy = False
    
    # For now, basic checks
    health_status['checks']['application'] = 'healthy'
    
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

# Graceful shutdown handling
class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        logger.info(f"Shutdown signal received: {signum}")
        self.shutdown_requested = True
        sys.exit(0)

shutdown_handler = GracefulShutdown()

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