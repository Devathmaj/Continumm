<![CDATA[# Continumm Backend

Production-ready Python backend providing REST APIs for network device inventory, telemetry data, and alerting, with built-in Prometheus metrics, structured JSON logging, and OpenTelemetry tracing.

---

## Responsibilities

- Serve REST API endpoints for device inventory, telemetry metrics, and alerts
- Expose Prometheus metrics at `/metrics` for scraping
- Run background telemetry workers (subnet discovery + device health polling)
- Manage PostgreSQL schema via SQLAlchemy ORM
- Emit structured JSON logs to stdout for Loki ingestion
- Export OpenTelemetry traces to Tempo (optional)

---

## Internal Architecture

```
backend/
├── app/
│   ├── app.py              # Flask app, routes, middleware, metrics, tracing
│   ├── config.py           # Environment-driven Config singleton
│   ├── db.py               # SQLAlchemy engine, session manager, leader lock
│   ├── models.py           # ORM: Device, DevicePort, DeviceStatus, AlertEvent, ScanRun
│   └── telemetry/
│       ├── __init__.py
│       ├── service.py      # TelemetryService: async orchestrator (discovery + polling loops)
│       ├── discovery.py    # ARP table, scapy ARP, nmap discovery + port enrichment
│       ├── monitoring.py   # ICMP ping parsing, HTTP probes
│       └── metrics.py      # Prometheus gauge/counter/histogram definitions
├── tests/                  # Test directory
├── Dockerfile              # Multi-stage: builder → runtime (non-root)
├── requirements.txt        # Pinned dependencies
├── .env.example            # Environment template
├── .dockerignore           # Build context exclusions
├── build.ps1 / build.sh    # Docker build scripts with git SHA tagging
└── verify.ps1              # Implementation verification checklist
```

### Request Lifecycle

1. Nginx forwards request to `backend:8000` on the internal network
2. `before_request` middleware generates a `request_id` and records start time
3. Flask route handler executes, querying PostgreSQL via `get_session()` context manager
4. `after_request` middleware records Prometheus metrics and emits a structured JSON log entry
5. If OpenTelemetry is enabled, the current span's `trace_id` and `span_id` are included in the log

### Telemetry Service Lifecycle

1. On startup, `TelemetryService.start()` spawns a daemon thread
2. The thread runs `asyncio.run()` with two concurrent tasks: `_discovery_loop` and `_polling_loop`
3. In K8s multi-replica scenarios, only the pod that acquires the PostgreSQL advisory lock runs telemetry
4. On SIGTERM/SIGINT, `GracefulShutdown` stops the service and releases the lock

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 2.3.3 | Web framework |
| Gunicorn | 21.2.0 | Production WSGI server |
| SQLAlchemy | 2.0.30 | ORM and database management |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| prometheus-client | 0.19.0 | Metrics instrumentation |
| aiohttp | 3.9.5 | Async HTTP client (probes) |
| scapy | 2.5.0 | Optional ARP scanning |
| opentelemetry-sdk | 1.25.0 | Distributed tracing |
| opentelemetry-instrumentation-flask | 0.46b0 | Flask auto-instrumentation |
| opentelemetry-exporter-otlp | 1.25.0 | OTLP trace export |

---

## API Endpoints

### Operational

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/` | GET | Service info | None |
| `/health` | GET | Dependency health (200/503) | None |
| `/metrics` | GET | Prometheus metrics | None |
| `/version` | GET | Git commit + environment | None |

### Telemetry

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/devices` | GET | List devices (query: `limit`) |
| `/api/devices/<id>` | GET | Single device with ports + status |
| `/api/devices/<id>/metrics` | GET | Device telemetry time series (query: `limit`) |
| `/api/alerts` | GET | Alert feed (query: `limit`) |
| `/api/telemetry/overview` | GET | Summary: device count, last scan, last alert |

All endpoints return JSON. Database-dependent endpoints return `503` with `{"error": "database_unavailable"}` if PostgreSQL is unreachable.

---

## Environment Variables

See the [root README environment variables section](../README.md#environment-variables) for the complete table.

Key variables: `PORT`, `HOST`, `DATABASE_URL`, `TELEMETRY_ENABLED`, `SCAN_SUBNETS`, `OTEL_ENABLED`.

---

## Local Development

### Without Docker

```bash
cd backend
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.\.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env as needed

python app/app.py
# Listening on http://localhost:8000
```

### With Docker

```powershell
cd backend
.\build.ps1             # Builds continumm-backend:<git-sha> + :latest
docker run -p 8000:8000 continumm-backend:latest
```

### Testing

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl http://localhost:8000/version
```

---

## Docker Image

### Multi-Stage Build

- **Stage 1 (builder):** Installs dependencies into `/opt/venv`
- **Stage 2 (runtime):** Copies venv + app code, installs `nmap` + `ping`, sets capabilities

### Security

- Runs as `appuser` (UID 1000), not root
- `cap_net_raw` granted to `ping` and `nmap` only
- Build context filtered by `.dockerignore`

### Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

### Build Arguments

| Arg | Purpose |
|-----|---------|
| `GIT_COMMIT` | Baked into `/app/.git_commit` for the `/version` endpoint |

---

## Deployment Notes

- In Docker Compose, the backend has **no host port binding**. It is only reachable via Nginx on the internal network.
- In Kubernetes, two separate Deployments exist: `backend` (API only, multiple replicas) and `backend-telemetry` (single replica with telemetry enabled and leader lock).
- Gunicorn runs with 4 workers and a 120s timeout.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `/health` returns 503 | Database unreachable | Check `DATABASE_URL` and Postgres container |
| No telemetry data | `TELEMETRY_ENABLED=false` | Set to `true` and configure `SCAN_SUBNETS` |
| `nmap binary not found` | nmap not installed | Verify Dockerfile installs nmap |
| Advisory lock not acquired | Another pod holds the lock | Normal in multi-replica; only one runs telemetry |
| High memory usage | Too many concurrent pings | Reduce `MAX_CONCURRENT_PINGS` |
]]>
