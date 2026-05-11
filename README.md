# Continumm

Production-ready backend service with complete observability stack.

## 🎯 What's Built

Two environments with separate stacks:

- ✅ **Local Docker stack** for fast testing
- ✅ **Kubernetes stack** for production-like validation

Each environment includes:

- ✅ **Backend Service** - Flask app with operational endpoints (/health, /metrics, /version)
- ✅ **Full Observability** - Prometheus metrics + Grafana dashboards + Loki logs
- ✅ **Production Docker** - Multi-stage builds, non-root user, immutable tags
- ✅ **Proper Isolation** - Backend not exposed publicly, only via Nginx
- ✅ **Real Monitoring** - RPS, p95 latency, error rate, CPU/memory metrics

## 🚀 Quick Start

### Local (Docker) Deploy

```powershell
# Windows
cd deploy
.\deploy.ps1

# Linux/Mac
cd deploy
chmod +x deploy.sh
./deploy.sh
```

### Access Services (Docker)

| Service | URL | Notes |
|---------|-----|-------|
| **Backend** | http://localhost | Via Nginx only (backend not exposed) |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Grafana** | http://localhost:3000 | Dashboards (admin/changeme) |
| **Loki** | http://localhost:3100 | Logs API (internal use) |

### Verify Everything Works

```powershell
cd deploy
.\test.ps1
```

## 📊 Observability Dashboard

Grafana dashboard includes:
- **RPS** (Requests Per Second) - Real-time traffic
- **p95 Latency** - 95th percentile response time
- **Error Rate** - Percentage of failed requests
- **CPU Usage** - Host CPU utilization
- **Memory Usage** - Host memory consumption
- **Per-Endpoint Metrics** - Breakdown by API endpoint

**If metrics don't make sense, your app is lying.** This stack ensures accurate observability.

## 🏗️ Architecture

```
Public Internet
      ↓
   Nginx:80 (ONLY public service)
      ↓
   Backend:8000 (Internal only)
      ↓
   Prometheus:9090 → Grafana:3000 → Loki:3100
      ↑
   Node Exporter (host metrics)
```

### Security Model

- ✅ Backend **NOT exposed** to host - only via internal Docker network
- ✅ Nginx **ONLY service** on port 80
- ✅ Prometheus/Grafana/Loki bound to **localhost only**
- ✅ Metrics ports **restricted**

## 📁 Structure

```
backend/
├── app/
│   └── app.py              # Flask app with /health, /metrics, /version
├── Dockerfile              # Multi-stage production build
├── requirements.txt        # Python dependencies
└── README.md              # Backend documentation

deploy/
├── docker-compose.yml      # Full production stack
├── deploy.ps1 / .sh       # Deployment scripts
├── test.ps1               # Verification script
├── nginx/
│   └── nginx.conf         # Reverse proxy config
├── prometheus/
│   └── prometheus.yml     # Scrape configuration
├── grafana/
│   └── provisioning/      # Auto-configured datasources + dashboards
├── loki/
│   └── loki.yml            # Loki configuration
└── k8s/                    # Kubernetes manifests (separate stack)
└── README.md              # Deployment documentation

infra/
├── ansible/               # Configuration management
└── terraform/             # Infrastructure as code
```

## 🔧 Key Features

### Backend Service
- **Operational Endpoints**: `/health`, `/metrics`, `/version`
- **Structured Logging**: JSON logs with request tracking
- **Environment Config**: All config via env vars (12-factor)
- **Graceful Shutdown**: Signal handlers for clean shutdown
- **Prometheus Metrics**: request_total, request_duration_seconds, error_total

### Docker Image
- **Multi-stage Build**: Builder + runtime stages for minimal size
- **Non-root User**: Runs as appuser (UID 1000)
- **Git SHA Tagging**: Immutable images tagged with commit hash
- **Health Checks**: Built-in container health monitoring

### Observability Stack
- **Prometheus**: Scrapes backend + node_exporter every 10-15s
- **Grafana**: Pre-configured dashboards with key metrics
- **Loki**: Centralized log storage with Grafana datasource
- **Node Exporter**: Host-level CPU, memory, disk metrics
- **Static Config**: Simple, no service discovery needed

## 🧪 Testing

### Test Backend Endpoints

```powershell
# Health check
curl http://localhost/health

# Version (includes git commit)
curl http://localhost/version

# Metrics (Prometheus format)
curl http://localhost/metrics
```

### Generate Load for Metrics

```powershell
# Simple load test
for ($i=0; $i -lt 100; $i++) {
    curl http://localhost/health
    Start-Sleep -Milliseconds 100
}
```

### Check Metrics

1. Open Grafana: http://localhost:3000 (admin/changeme)
2. Navigate to "Continumm Backend - Production Metrics" dashboard
3. Observe RPS, latency, error rate updating in real-time

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

## 📝 Documentation

- [Backend README](backend/README.md) - Service implementation details
- [Deploy README](deploy/README.md) - Complete deployment guide
- [Kubernetes Manifests](deploy/k8s/README.md) - K8s apply and access

## ✅ Deliverables Checklist

### Step 1: Backend Service
- [x] `/health` returns 200 only if dependencies healthy
- [x] `/metrics` exposes request_total, request_duration_seconds_bucket, error_total
- [x] `/version` returns git commit hash
- [x] Structured logs (JSON)
- [x] Config only via env vars
- [x] App starts and stops cleanly

### Step 2: Containerization
- [x] Multi-stage Dockerfile
- [x] Non-root user
- [x] Explicit EXPOSE
- [x] No shell scripts doing "magic"
- [x] Immutable image with git SHA tag
- [x] Runs identically everywhere

### Step 3: Observability Stack
- [x] Prometheus scrapes backend
- [x] Prometheus scrapes node_exporter
- [x] Loki for log aggregation
- [x] Grafana dashboard with RPS, p95 latency, error rate, CPU/memory
- [x] Metrics validation (if they don't make sense, app is lying)

### Step 4: Docker Compose
- [x] Services: backend, nginx, prometheus, grafana, loki, node_exporter
- [x] Backend not exposed publicly
- [x] Only Nginx binds to port 80
- [x] Metrics ports restricted
- [x] Complete "mini production" environment

### Step 5: Reverse Proxy (Nginx)
- [x] Zero-downtime reloads with graceful reload scripts
- [x] Health-aware routing with automatic failover
- [x] Explicit timeout configuration (5s connect, 60s read/send)
- [x] Retry logic for failed upstream requests
- [x] Rate limiting and security headers
- [x] Blast radius control

### Step 6: Infrastructure as Code (Terraform)
- [x] VM provisioning (Azure Ubuntu 22.04)
- [x] Security groups (SSH, HTTP, HTTPS)
- [x] SSH key-based authentication (no passwords)
- [x] Disk configuration (OS + Data disk)
- [x] Cloud-init automated setup (Docker, system tuning)
- [x] No manual setup - terraform apply creates working VM
- [x] 100% reproducible infrastructure

## 🔒 Production-Ready Features

- **Immutable Deployments**: Git SHA tagged images
- **Health Monitoring**: All services have health checks
- **Log Management**: JSON structured logs, log rotation
- **Resource Limits**: Proper logging limits configured
- **Network Isolation**: Services on private network
- **Security Headers**: Nginx configured with security best practices
- **Rate Limiting**: 10 req/s with burst capacity

## 🚦 Next Steps

- [ ] Add database integration with health checks
- [ ] Implement authentication/authorization
- [ ] Add CI/CD pipeline
- [ ] Configure alerting rules in Prometheus
- [ ] Add distributed tracing (Jaeger/Tempo)
- [ ] Implement backup strategy
- [ ] Add SSL/TLS termination
- [ ] Scale to multi-node with Kubernetes

## ☸️ Kubernetes Runbook

Use this to deploy the Kubernetes stack (separate from Docker Compose):

```bash
docker build -t continumm-backend:latest ./backend

# For kind:
kind load docker-image continumm-backend:latest

# For minikube:
# minikube image load continumm-backend:latest

kubectl apply -k deploy/k8s
```

Access:
- App via Ingress: http://continumm.local (map to your ingress IP)
- Prometheus:
   ```bash
   kubectl -n continumm port-forward svc/prometheus 9090:9090
   ```
- Grafana:
   ```bash
   kubectl -n continumm port-forward svc/continumm-grafana 3000:3000
   ```

## 📚 Additional Documentation

- [Backend Implementation](backend/README.md) - Service details
- [Deployment Guide](deploy/README.md) - Complete stack deployment  
- [Nginx Configuration](deploy/NGINX.md) - Zero-downtime and health-aware routing
- [Terraform Guide](infra/terraform/README.md) - Infrastructure provisioning
- [Implementation Summary](IMPLEMENTATION.md) - Detailed technical overview
- [Steps 5 & 6](STEPS_5_6.md) - Nginx and Terraform implementation
- [Quick Reference](QUICKSTART.md) - Common commands

## 📄 License

MIT

Please read the contributing guidelines.