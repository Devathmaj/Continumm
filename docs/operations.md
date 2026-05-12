<![CDATA[# Continumm — Operations Runbook

This document covers day-to-day operations, maintenance, and incident response procedures.

---

## Service Management

### Docker Compose Commands

```bash
# Start all services
cd deploy && docker-compose up -d

# Stop all services (preserves volumes)
docker-compose down

# Stop and destroy all data
docker-compose down -v

# Restart a single service
docker-compose restart backend

# Rebuild backend after code changes
docker-compose up -d --build backend

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f prometheus

# Check service status
docker-compose ps

# Resource usage
docker stats
```

### Health Checks

```bash
# Application health
curl http://localhost/health

# Prometheus health
curl http://localhost:9090/-/healthy

# Grafana health
curl http://localhost:3001/api/health

# Container health status
docker inspect --format='{{.State.Health.Status}}' continumm-backend
docker inspect --format='{{.State.Health.Status}}' continumm-nginx
docker inspect --format='{{.State.Health.Status}}' continumm-prometheus
```

---

## Nginx Operations

### Zero-Downtime Configuration Reload

```powershell
# Windows
cd deploy
.\reload-nginx.ps1
```

```bash
# Linux/macOS
cd deploy
./reload-nginx.sh
```

The script: validates config → sends `nginx -s reload` → verifies the service responds.

### Manual Reload

```bash
# Validate config first (always!)
docker-compose exec nginx nginx -t

# Reload if valid
docker-compose exec nginx nginx -s reload
```

### Rate Limit Tuning

Edit `deploy/nginx/nginx.conf`:
```nginx
# Current: 10 req/s per IP with burst of 20
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;

# High traffic: 50 req/s per IP with burst of 100
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=50r/s;
limit_req zone=api_limit burst=100 nodelay;
```

Reload Nginx after changes.

---

## Backup and Recovery

### PostgreSQL Backup

```bash
# Dump database
docker-compose exec postgres pg_dump -U continumm continumm > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20260115.sql | docker-compose exec -T postgres psql -U continumm continumm
```

### Volume Backup

```bash
# Prometheus data
docker run --rm -v deploy_prometheus-data:/data -v $(pwd):/backup ubuntu tar czf /backup/prometheus-backup.tar.gz /data

# Grafana data
docker run --rm -v deploy_grafana-data:/data -v $(pwd):/backup ubuntu tar czf /backup/grafana-backup.tar.gz /data

# PostgreSQL data
docker run --rm -v deploy_postgres-data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres-backup.tar.gz /data
```

### Volume Restore

```bash
docker-compose down
docker run --rm -v deploy_prometheus-data:/data -v $(pwd):/backup ubuntu bash -c "cd /data && tar xzf /backup/prometheus-backup.tar.gz --strip-components=1"
docker-compose up -d
```

---

## Monitoring Procedures

### Prometheus Targets

Check that all scrape targets are UP: http://localhost:9090/targets

Expected targets:
| Job | Target | Interval |
|-----|--------|----------|
| `backend` | `backend:8000` | 10s |
| `node_exporter` | `node_exporter:9100` | 15s |
| `prometheus` | `localhost:9090` | 15s |
| `alertmanager` | `alertmanager:9093` | 15s |

### Key Grafana Dashboards

1. **Continumm Backend** — Application performance (RPS, latency percentiles, error rate, CPU, memory)
2. **Continumm Network** — Device health (online status, latency, packet loss, discovery counts)

Access: http://localhost:3001 → Dashboards

### Alert Verification

```bash
# Check firing alerts in Prometheus
curl http://localhost:9090/api/v1/alerts

# Check Alertmanager status
docker-compose exec alertmanager amtool alert --alertmanager.url=http://localhost:9093

# View alert rules
curl http://localhost:9090/api/v1/rules
```

---

## Scaling

### Vertical Scaling (Docker Compose)

Edit `docker-compose.yml` to increase Gunicorn workers:
```yaml
# In backend CMD or entrypoint
CMD ["gunicorn", "--workers", "8", ...]
```

### Horizontal Scaling (Kubernetes)

```bash
# Scale API replicas
kubectl -n continumm scale deployment backend --replicas=4

# Verify pods
kubectl -n continumm get pods -l app=backend
```

> **Note:** Only one telemetry worker should run. The advisory lock ensures this automatically.

---

## Log Analysis

### Structured Log Format

Every backend log line is JSON:
```json
{
  "timestamp": "2026-01-15T12:00:00.000000Z",
  "level": "INFO",
  "message": "GET /health 200",
  "logger": "continumm",
  "request_id": "a1b2c3d4e5f6g7h8",
  "path": "/health",
  "method": "GET",
  "status_code": 200,
  "duration": 0.0042
}
```

### Useful Log Queries (Grafana → Explore → Loki)

```logql
# All errors
{container="continumm-backend"} |= "ERROR"

# Slow requests (>1s)
{container="continumm-backend"} | json | duration > 1

# Telemetry discovery logs
{container="continumm-backend"} |= "discovery"

# Specific request_id
{container="continumm-backend"} |= "a1b2c3d4"
```

---

## Incident Response

### Backend Not Responding

1. Check container status: `docker-compose ps backend`
2. Check logs: `docker-compose logs --tail=50 backend`
3. Check health: `docker-compose exec nginx wget -O- http://backend:8000/health`
4. If OOM-killed: increase memory limits or reduce Gunicorn workers
5. Restart: `docker-compose restart backend`

### Database Connection Failures

1. Check Postgres: `docker-compose ps postgres`
2. Test connectivity: `docker-compose exec postgres pg_isready`
3. Check connection pool: look for "pool exhausted" in backend logs
4. Verify `DATABASE_URL` in environment

### Disk Space Issues

```bash
# Check Docker disk usage
docker system df

# Prune unused resources
docker system prune -f

# Check volume sizes
docker system df -v
```

### Prometheus Out of Memory

Reduce retention or cardinality:
```yaml
command:
  - '--storage.tsdb.retention.time=7d'  # Reduce from 30d
```

---

## Update Procedures

### Application Update

```bash
cd deploy
git pull origin main
./deploy.sh    # Rebuilds image with new git SHA, restarts stack
```

### Observability Stack Update

Update image tags in `docker-compose.yml`, then:
```bash
docker-compose pull prometheus grafana loki tempo alertmanager
docker-compose up -d
```

### Terraform Infrastructure Update

```powershell
cd infra/terraform
terraform plan    # Review changes
terraform apply   # Apply changes
```
]]>
