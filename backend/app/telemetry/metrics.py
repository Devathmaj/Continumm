from prometheus_client import Counter, Gauge, Histogram

DISCOVERY_SCAN_DURATION = Histogram(
    "discovery_scan_duration_seconds",
    "Discovery scan duration in seconds",
    ["subnet"],
)
DISCOVERY_SCAN_FAILURES = Counter(
    "discovery_scan_failures_total",
    "Total discovery scan failures",
    ["subnet"],
)
DISCOVERY_DEVICES_FOUND = Gauge(
    "discovery_devices_found",
    "Devices discovered in the last scan",
    ["subnet"],
)
DISCOVERY_ACTIVE_DEVICES = Gauge(
    "discovery_active_devices",
    "Active devices discovered across subnets",
)

POLLING_RUN_DURATION = Histogram(
    "polling_run_duration_seconds",
    "Polling run duration in seconds",
)
POLLING_FAILURES = Counter(
    "polling_failures_total",
    "Total polling failures",
)
POLLING_QUEUE_DEPTH = Gauge(
    "polling_queue_depth",
    "Queue depth for polling tasks",
)
WORKER_LAST_RUN_TIMESTAMP = Gauge(
    "worker_last_run_timestamp",
    "Unix timestamp of last worker execution",
    ["worker"],
)

DEVICE_ONLINE = Gauge(
    "network_device_online",
    "Device online status",
    ["ip", "device_id"],
)
DEVICE_LATENCY_MS = Gauge(
    "network_device_latency_ms",
    "Device latency in milliseconds",
    ["ip", "device_id"],
)
DEVICE_PACKET_LOSS_PERCENT = Gauge(
    "network_device_packet_loss_percent",
    "Device packet loss percentage",
    ["ip", "device_id"],
)
DEVICE_JITTER_MS = Gauge(
    "network_device_jitter_ms",
    "Device jitter in milliseconds",
    ["ip", "device_id"],
)
DEVICE_RESPONSE_TIME_MS = Gauge(
    "network_device_response_time_ms",
    "Device response time in milliseconds",
    ["ip", "device_id"],
)
DEVICE_UPTIME_PERCENT = Gauge(
    "network_device_uptime_percent",
    "Device uptime percentage",
    ["ip", "device_id"],
)
DEVICE_OPEN_PORT = Gauge(
    "network_device_open_port",
    "Device open port",
    ["ip", "port", "service"],
)
DEVICE_INFO = Gauge(
    "network_device_info",
    "Device inventory information",
    ["ip", "device_id", "hostname", "mac_address", "vendor"],
)

ALERTS_TOTAL = Counter(
    "network_alerts_total",
    "Total alert events emitted by the backend",
    ["alert_type", "severity"],
)
