import os


def _env_bool(name, default="false"):
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def _env_list(name, default=""):
    value = os.getenv(name, default).strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    TELEMETRY_ENABLED = _env_bool("TELEMETRY_ENABLED", "false")
    TELEMETRY_DISABLE_LEADER_LOCK = _env_bool("TELEMETRY_DISABLE_LEADER_LOCK", "false")
    TELEMETRY_LEADER_LOCK_KEY = int(os.getenv("TELEMETRY_LEADER_LOCK_KEY", "42004200"))

    DISCOVERY_INTERVAL_SECONDS = int(os.getenv("DISCOVERY_INTERVAL_SECONDS", "300"))
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
    SCAN_SUBNETS = _env_list("SCAN_SUBNETS", "")

    SCAN_USE_ARP = _env_bool("SCAN_USE_ARP", "true")
    SCAN_USE_SCAPY = _env_bool("SCAN_USE_SCAPY", "false")
    SCAN_USE_NMAP = _env_bool("SCAN_USE_NMAP", "true")

    PORT_SCAN_ENABLED = _env_bool("PORT_SCAN_ENABLED", "false")
    PORT_SCAN_TOP_PORTS = int(os.getenv("PORT_SCAN_TOP_PORTS", "50"))
    PORT_SCAN_LIMIT = int(os.getenv("PORT_SCAN_LIMIT", "25"))

    NMAP_PATH = os.getenv("NMAP_PATH", "nmap")
    NMAP_MIN_RATE = os.getenv("NMAP_MIN_RATE", "")
    NMAP_MAX_RATE = os.getenv("NMAP_MAX_RATE", "")
    NMAP_DISABLE_ARP_PING = _env_bool("NMAP_DISABLE_ARP_PING", "false")

    PING_COUNT = int(os.getenv("PING_COUNT", "3"))
    PING_TIMEOUT_SECONDS = int(os.getenv("PING_TIMEOUT_SECONDS", "1"))
    MAX_CONCURRENT_PINGS = int(os.getenv("MAX_CONCURRENT_PINGS", "50"))

    HTTP_PROBE_ENABLED = _env_bool("HTTP_PROBE_ENABLED", "false")
    HTTP_PROBE_TIMEOUT_SECONDS = float(os.getenv("HTTP_PROBE_TIMEOUT_SECONDS", "2.0"))

    ALERT_OFFLINE_AFTER = int(os.getenv("ALERT_OFFLINE_AFTER", "3"))
    ALERT_LATENCY_MS = float(os.getenv("ALERT_LATENCY_MS", "200"))
    ALERT_PACKET_LOSS_PERCENT = float(os.getenv("ALERT_PACKET_LOSS_PERCENT", "20"))
    ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))

    OTEL_ENABLED = _env_bool("OTEL_ENABLED", "false")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "continumm-backend")
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")


config = Config()
