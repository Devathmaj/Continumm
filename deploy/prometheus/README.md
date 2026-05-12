# Prometheus Configuration

Prometheus scrapes metrics from the backend and Node Exporter, evaluates alert rules, and forwards firing alerts to Alertmanager.

## Scrape Targets

| Job | Target | Interval | Path |
|-----|--------|----------|------|
| `backend` | `backend:8000` | 10s | `/metrics` |
| `node_exporter` | `node_exporter:9100` | 15s | `/metrics` |
| `prometheus` | `localhost:9090` | 15s | `/metrics` |
| `alertmanager` | `alertmanager:9093` | 15s | `/metrics` |

## Alert Rules (`alert_rules.yml`)

| Alert | Expression | Duration | Severity |
|-------|-----------|----------|----------|
| `NetworkDeviceOffline` | `network_device_online == 0` | 2m | critical |
| `NetworkLatencyHigh` | `network_device_latency_ms > 200` | 5m | warning |
| `NetworkPacketLossHigh` | `network_device_packet_loss_percent > 20` | 5m | warning |
| `NetworkDeviceFlapping` | `changes(network_device_online[10m]) > 4` | 5m | warning |

## Storage

- **Retention:** 30 days (`--storage.tsdb.retention.time=30d`)
- **Volume:** `prometheus-data` Docker volume (50Gi PVC in K8s)
- **Access:** `127.0.0.1:9090` in Docker Compose (localhost only)

## Files

- `prometheus.yml` — Global settings, scrape configs, alertmanager target
- `alert_rules.yml` — Network telemetry alerting rules

## Verify Targets

Open http://localhost:9090/targets — all targets should show **UP**.

