<![CDATA[# Continumm — Deploy

Complete production deployment stack with Docker Compose orchestration, reverse proxy, and full observability pipeline.

---

## Architecture

```mermaid
graph TB
    subgraph "Host Machine"
        direction TB
        P80[":80"] --> Nginx
        P9090["127.0.0.1:9090"] --> Prometheus
        P3001["127.0.0.1:3001"] --> Grafana
    end

    subgraph "continumm-internal (172.30.0.0/16)"
        Nginx["Nginx<br/>Reverse proxy · Rate limit"]
        Backend["Backend :8000<br/>Flask + Gunicorn"]
        Postgres["PostgreSQL :5432"]
        Prometheus["Prometheus :9090<br/>30d retention"]
        Grafana["Grafana :3000<br/>Pre-loaded dashboards"]
        Loki["Loki :3100<br/>Log aggregation"]
        Tempo["Tempo :4317<br/>Trace storage"]
        AM["Alertmanager :9093<br/>Alert routing"]
        NE["Node Exporter :9100<br/>Host metrics"]
    end

    Nginx --> Backend
    Backend --> Postgres
    Prometheus -->|scrape /metrics| Backend
    Prometheus -->|scrape| NE
    Prometheus -->|alerts| AM
    Grafana --> Prometheus
    Grafana --> Loki
    Grafana --> Tempo
    Backend -->|OTLP gRPC| Tempo
```

---

## Services

| Service | Container | Exposed Port | Purpose |
|---------|-----------|-------------|---------|
| Backend | `continumm-backend` | Internal only | Flask API + telemetry workers |
| Nginx | `continumm-nginx` | `:80` (public) | Reverse proxy, rate limiting, security headers |
| PostgreSQL | `continumm-postgres` | Internal only | Device inventory, telemetry, alerts |
| Prometheus | `continumm-prometheus` | `127.0.0.1:9090` | Metrics scraping and storage (30d retention) |
| Grafana | `continumm-grafana` | `127.0.0.1:3001` | Dashboards and visualization |
| Loki | `continumm-loki` | Internal only | Log aggregation |
| Tempo | `continumm-tempo` | Internal only | Distributed trace storage |
| Alertmanager | `continumm-alertmanager` | Internal only | Alert deduplication and routing |
| Node Exporter | `continumm-node-exporter` | Internal only | Host-level CPU/memory/disk/network metrics |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (for commit SHA tagging)
- Ports 80, 3001, 9090 available

### Deploy

**Windows:**
```powershell
cd deploy
.\deploy.ps1
```

**Linux / macOS:**
```bash
cd deploy
chmod +x deploy.sh
./deploy.sh
```

The script automatically:
1. Captures git commit hash
2. Creates `.env` from `.env.example` if missing
3. Writes `GIT_COMMIT` into `.env`
4. Builds the backend Docker image with git SHA tag
5. Runs `docker-compose down` then `docker-compose up -d`

### Manual Deploy

```bash
export GIT_COMMIT=$(git rev-parse HEAD)
docker build --build-arg GIT_COMMIT=$GIT_COMMIT -t continumm-backend:latest ../backend
docker-compose up -d
```

---

## Access

| Service | URL | Credentials |
|---------|-----|-------------|
| Application | http://localhost | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | `admin` / `changeme` |

Change Grafana password via `GRAFANA_ADMIN_PASSWORD` in `.env`.

---

## Configuration

### Environment File

Copy `.env.example` to `.env` and customize:

| Variable | Default | Purpose |
|----------|---------|---------|
| `GIT_COMMIT` | `unknown` | Backend image version label |
| `GRAFANA_ADMIN_PASSWORD` | `changeme` | Grafana admin password |
| `POSTGRES_USER` | `continumm` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `continumm` | PostgreSQL password |
| `POSTGRES_DB` | `continumm` | PostgreSQL database |
| `TELEMETRY_ENABLED` | `false` | Enable network scanning |
| `SCAN_SUBNETS` | _(empty)_ | CIDR list to scan |
| `DATABASE_URL` | `postgresql://continumm:continumm@postgres:5432/continumm` | DB connection |

### Enable Telemetry

Edit `.env`:
```env
TELEMETRY_ENABLED=true
SCAN_SUBNETS=192.168.1.0/24,10.0.0.0/24
```

Restart: `docker-compose down && docker-compose up -d`

---

## Docker Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| `prometheus-data` | Prometheus | Time-series metrics (30d retention) |
| `grafana-data` | Grafana | Dashboards, datasources, preferences |
| `loki-data` | Loki | Log storage |
| `postgres-data` | PostgreSQL | Device inventory, telemetry, alerts |

---

## Common Operations

### View Logs
```bash
docker-compose logs -f              # All services
docker-compose logs -f backend      # Backend only
docker-compose logs -f nginx        # Nginx only
```

### Check Status
```bash
docker-compose ps
docker stats
```

### Restart a Service
```bash
docker-compose restart backend
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build backend
```

### Full Stack Reset
```bash
docker-compose down -v    # Destroys all data
docker-compose up -d
```

### Nginx Zero-Downtime Reload
```powershell
.\reload-nginx.ps1        # Windows
./reload-nginx.sh         # Linux/macOS
```

---

## Stack Verification

```powershell
.\test.ps1
```

This script checks:
- All required services are running
- Backend health, version, and metrics endpoints respond
- Backend is NOT directly accessible on port 8000 (isolation verified)
- All Prometheus scrape targets are UP
- Generates sample traffic for dashboard testing

---

## Security Model

- **Backend isolation** — No host port binding; only reachable via Nginx
- **Metrics restriction** — Prometheus and Grafana bound to `127.0.0.1`
- **Rate limiting** — 10 req/s per IP with burst of 20
- **Security headers** — X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Isolated network** — All services on `172.30.0.0/16` bridge
- **Log rotation** — JSON file driver with 10MB max, 3 files per container

---

## File Structure

```
deploy/
├── docker-compose.yml          # 9-service stack definition
├── .env.example                # Environment variable template
├── deploy.ps1 / deploy.sh      # One-command deployment
├── test.ps1                    # Stack verification
├── reload-nginx.ps1/.sh        # Zero-downtime Nginx reload
├── NGINX.md                    # Nginx operations guide
├── nginx/nginx.conf            # Reverse proxy configuration
├── prometheus/
│   ├── prometheus.yml          # Scrape targets and intervals
│   └── alert_rules.yml         # Network telemetry alert rules
├── grafana/provisioning/
│   ├── datasources/            # Prometheus, Loki, Tempo auto-config
│   └── dashboards/             # Pre-built JSON dashboards
├── loki/loki.yml               # Log aggregation config
├── tempo/tempo.yml             # Trace storage config
├── alertmanager/alertmanager.yml  # Alert routing config
└── k8s/                        # Kubernetes manifests
```

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Port 80 in use | `netstat -ano \| findstr :80` and stop conflicting process |
| Backend unreachable at `:8000` | Correct — use `http://localhost/` via Nginx |
| Prometheus target DOWN | `docker-compose exec prometheus wget -O- http://backend:8000/health` |
| Grafana dashboard empty | Generate traffic, wait 30s for scrape interval |
| Services won't start | `docker-compose logs` then `docker-compose down -v && docker-compose up -d` |
| Disk space issues | `docker system prune -f` and `docker system df` |
]]>
