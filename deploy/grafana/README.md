# Grafana Configuration

Grafana provides visualization dashboards for application and network telemetry metrics. It is pre-configured with datasources and dashboards via provisioning — no manual setup required.

## Datasources (auto-provisioned)

| Datasource | Type | URL | Purpose |
|-----------|------|-----|---------|
| Prometheus | `prometheus` | `http://prometheus:9090` | Application and network metrics |
| Loki | `loki` | `http://loki:3100` | Log aggregation and search |
| Tempo | `tempo` | `http://tempo:3200` | Distributed trace queries |

## Dashboards (auto-provisioned)

| Dashboard | File | Content |
|-----------|------|---------|
| Continumm Backend | `continumm-backend.json` | RPS, p50/p95/p99 latency, error rate, HTTP status codes, CPU, memory, per-endpoint metrics |
| Continumm Network | `continumm-network.json` | Device online status, latency, packet loss, jitter, discovery scan metrics, alert counts |

## Access

- **Docker Compose:** http://localhost:3001 (`admin` / `changeme`)
- **Kubernetes:** `kubectl -n continumm port-forward svc/continumm-grafana 3000:3000`

Change password via `GRAFANA_ADMIN_PASSWORD` in `deploy/.env`.

## File Structure

```
grafana/provisioning/
├── datasources/
│   ├── prometheus.yml    # Prometheus datasource
│   ├── loki.yml          # Loki datasource
│   └── tempo.yml         # Tempo datasource
└── dashboards/
    ├── dashboard.yml             # Dashboard provider config
    ├── continumm-backend.json    # Application metrics dashboard
    └── continumm-network.json    # Network telemetry dashboard
```

## Customization

To add a new dashboard: export JSON from Grafana UI → save to `provisioning/dashboards/` → restart Grafana.

