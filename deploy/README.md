# Continumm Production Stack

Complete production deployment with full observability stack.

## Architecture

```
┌─────────────────┐
│   Public Web    │
└────────┬────────┘
         │ :80
         ▼
┌─────────────────┐
│  Nginx (Proxy)  │
└────────┬────────┘
         │ Internal Network
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Backend:8000   │─────▶│  Prometheus:9090 │
│  (Not Exposed)  │      │  (localhost only)│
└─────────────────┘      └────────┬─────────┘
         │                        │
         │                        ▼
         │               ┌──────────────────┐
         │               │  Grafana:3000    │
         │               │  (localhost only)│
         └──────────────▶└──────────────────┘
                         
┌─────────────────┐
│ Node Exporter   │──────▶ Prometheus
│    :9100        │       (Internal only)
└─────────────────┘
```

## Services

### Backend (continumm-backend)
- **NOT exposed publicly** - Only accessible via internal Docker network
- Exposes `/metrics` endpoint for Prometheus scraping
- Structured JSON logging
- Health checks via `/health`
- Configuration via environment variables

### Nginx (continumm-nginx)
- **ONLY service exposed to host** - Port 80
- Reverse proxy to backend
- Rate limiting: 10 req/s with burst of 20
- Security headers
- Health check proxying
- Request/response logging

### Prometheus (continumm-prometheus)
- **Restricted access** - Bound to localhost:9090 only
- Scrapes backend `/metrics` every 10s
- Scrapes node_exporter every 15s
- 30-day data retention
- Persistent storage via Docker volume

### Grafana (continumm-grafana)
- **Restricted access** - Bound to localhost:3000 only
- Pre-configured with Prometheus datasource
- Auto-loaded dashboard with:
  - RPS (Requests Per Second)
  - p95/p99/p50 Latency
  - Error Rate
  - HTTP Status Codes
  - CPU Usage
  - Memory Usage
  - Per-endpoint metrics
- Default credentials: admin/changeme

### Node Exporter (continumm-node-exporter)
- **Internal only** - No host port binding
- Collects host-level metrics
- CPU, memory, disk, network statistics

## Security Model

✅ **Backend Isolation**
- No public port exposure
- Only accessible via Nginx on internal network
- Cannot be reached directly from host

✅ **Metrics Restriction**
- Prometheus bound to 127.0.0.1 only
- Grafana bound to 127.0.0.1 only
- Metrics ports not accessible from external network

✅ **Public Access**
- Only Nginx on port 80
- Rate limiting enabled
- Security headers configured

## Deployment

### Prerequisites
- Docker and Docker Compose installed
- Git repository initialized
- Ports 80, 3000, 9090 available

### Deploy

**Windows:**
```powershell
cd deploy
.\deploy.ps1
```

**Linux/Mac:**
```bash
cd deploy
chmod +x deploy.sh
./deploy.sh
```

The deployment script:
1. Captures git commit hash
2. Creates `.env` file from template
3. Builds backend Docker image with git SHA tag
4. Starts all services with docker-compose
5. Displays access URLs

### Manual Deployment

```powershell
# Set git commit
$env:GIT_COMMIT = git rev-parse HEAD

# Build backend
docker build --build-arg GIT_COMMIT=$env:GIT_COMMIT -t continumm-backend:latest ../backend

# Start stack
cd deploy
docker-compose up -d
```

## Access

| Service | URL | Access |
|---------|-----|--------|
| Backend (via Nginx) | http://localhost | Public |
| Nginx Status | http://localhost/nginx_status | Internal only |
| Prometheus | http://localhost:9090 | Localhost only |
| Grafana | http://localhost:3000 | Localhost only |

**Grafana Default Credentials:**
- Username: `admin`
- Password: `changeme` (change via GRAFANA_ADMIN_PASSWORD in .env)

## Testing

### Test Backend via Nginx
```powershell
# Health check
curl http://localhost/health

# Version info (includes git commit)
curl http://localhost/version

# Metrics (Prometheus format)
curl http://localhost/metrics

# Main endpoint
curl http://localhost/
```

### Generate Load for Testing Metrics
```powershell
# Simple load test
for ($i=0; $i -lt 100; $i++) {
    curl http://localhost/health
    Start-Sleep -Milliseconds 100
}
```

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f prometheus
```

### Check Service Health
```powershell
# Service status
docker-compose ps

# Individual health checks
docker inspect --format='{{.State.Health.Status}}' continumm-backend
docker inspect --format='{{.State.Health.Status}}' continumm-nginx
docker inspect --format='{{.State.Health.Status}}' continumm-prometheus
```

## Metrics Validation

The Grafana dashboard shows these key metrics. If they don't make sense, the app is lying:

### ✅ RPS (Requests Per Second)
- Should increase with load
- Formula: `sum(rate(request_total[1m]))`
- Sanity check: Load test should show proportional RPS

### ✅ p95 Latency
- Should be consistent under normal load
- Formula: `histogram_quantile(0.95, sum(rate(request_duration_seconds_bucket[5m])) by (le))`
- Sanity check: Health endpoint should be <100ms at p95

### ✅ Error Rate
- Should be near 0% for healthy system
- Formula: `sum(rate(error_total[5m])) / sum(rate(request_total[5m]))`
- Sanity check: Valid requests should not produce errors

### ✅ CPU / Memory
- Should be stable under normal operation
- CPU: `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Memory: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
- Sanity check: Should not exceed 90% without load

## Prometheus Targets

Check scrape targets: http://localhost:9090/targets

All targets should show status: **UP**
- backend (http://backend:8000/metrics)
- node_exporter (http://node_exporter:9100/metrics)
- prometheus (http://localhost:9090/metrics)

## Troubleshooting

### Backend Not Accessible Directly
✅ **This is correct!** Backend should NOT be accessible from host.
- Only accessible via Nginx
- Test via: `curl http://localhost/health`

### Prometheus Can't Reach Backend
```powershell
# Check network connectivity
docker-compose exec prometheus wget -O- http://backend:8000/health
```

### Grafana Dashboard Empty
1. Check Prometheus is scraping: http://localhost:9090/targets
2. Verify metrics exist: http://localhost:9090/graph
3. Generate traffic: `curl http://localhost/health` multiple times
4. Wait 30 seconds for scrape interval

### Services Won't Start
```powershell
# Check logs
docker-compose logs

# Verify ports are available
netstat -ano | findstr ":80 :3000 :9090"

# Clean restart
docker-compose down -v
docker-compose up -d
```

## Maintenance

### Update Backend
```powershell
cd deploy
.\deploy.ps1  # Rebuilds and redeploys
```

### View Resource Usage
```powershell
docker stats
```

### Backup Metrics Data
```powershell
# Stop services
docker-compose down

# Backup volumes
docker run --rm -v deploy_prometheus-data:/data -v ${PWD}:/backup ubuntu tar czf /backup/prometheus-backup.tar.gz /data
docker run --rm -v deploy_grafana-data:/data -v ${PWD}:/backup ubuntu tar czf /backup/grafana-backup.tar.gz /data
```

### Clean Up
```powershell
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all metrics data)
docker-compose down -v
```

## Configuration Files

```
deploy/
├── docker-compose.yml          # Service orchestration
├── .env.example               # Environment template
├── deploy.ps1 / deploy.sh     # Deployment scripts
├── nginx/
│   └── nginx.conf            # Nginx reverse proxy config
├── prometheus/
│   └── prometheus.yml        # Scrape configuration
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── prometheus.yml    # Auto-configure Prometheus
        └── dashboards/
            ├── dashboard.yml     # Dashboard provider config
            └── continumm-backend.json  # Main dashboard
```

## Production Checklist

- [x] Backend not exposed publicly
- [x] Only Nginx binds to port 80
- [x] Metrics ports restricted to localhost
- [x] All services on isolated network
- [x] Health checks configured
- [x] Structured logging enabled
- [x] Prometheus scraping backend and node_exporter
- [x] Grafana dashboard with RPS, latency, errors, CPU, memory
- [x] Persistent storage for metrics
- [x] Git commit tracking
- [x] Rate limiting on Nginx
- [x] Security headers configured

---

**This is your mini production environment.** Everything that should work in production works here.
