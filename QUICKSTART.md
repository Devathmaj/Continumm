# Continumm Quick Reference

## 🚀 Deploy Everything
```powershell
cd deploy
.\deploy.ps1
```

## 🧪 Test Stack
```powershell
cd deploy
.\test.ps1
```

## 🔗 Access URLs
| Service | URL | Credentials |
|---------|-----|-------------|
| Backend | http://localhost | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/changeme |

## 📊 API Endpoints
```powershell
# Health check
curl http://localhost/health

# Version (git commit)
curl http://localhost/version

# Prometheus metrics
curl http://localhost/metrics
```

## 🔍 View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f nginx
docker-compose logs -f prometheus
```

## 📈 Generate Test Traffic
```powershell
for ($i=0; $i -lt 100; $i++) {
    curl http://localhost/health
    Start-Sleep -Milliseconds 100
}
```

## 🛑 Stop Services
```powershell
cd deploy
docker-compose down
```

## 🗑️ Clean Everything (including data)
```powershell
cd deploy
docker-compose down -v
```

## 🔄 Rebuild and Restart
```powershell
cd deploy
docker-compose down
.\deploy.ps1
```

## 📊 Grafana Dashboard
1. Open http://localhost:3000
2. Login: admin / changeme
3. Navigate to Dashboards → "Continumm Backend - Production Metrics"

## ✅ Verify Backend Isolation
```powershell
# This should FAIL (backend not exposed)
curl http://localhost:8000/health

# This should SUCCEED (via Nginx)
curl http://localhost/health
```

## 📦 Check Service Status
```powershell
docker-compose ps
docker-compose top
docker stats
```

## 🔍 Check Prometheus Targets
Open http://localhost:9090/targets

All should show status: **UP**

## 🐛 Troubleshooting

### Services won't start
```powershell
docker-compose logs
docker-compose down -v
docker-compose up -d
```

### Metrics not showing
```powershell
# Check Prometheus targets
# Open http://localhost:9090/targets

# Generate traffic
curl http://localhost/health

# Wait 30 seconds for scrape
```

### Port already in use
```powershell
# Check what's using the port
netstat -ano | findstr ":80"
netstat -ano | findstr ":3000"
netstat -ano | findstr ":9090"
```

## 📁 Key Files
```
backend/app/app.py              # Backend application
backend/Dockerfile              # Container build
deploy/docker-compose.yml       # Stack orchestration
deploy/nginx/nginx.conf         # Reverse proxy
deploy/prometheus/prometheus.yml # Metrics scraping
deploy/grafana/.../continumm-backend.json # Dashboard
```

## 🎯 Architecture Summary
```
Public → Nginx:80 → Backend:8000 (internal)
                    ↓
                    Prometheus:9090 → Grafana:3000
                    ↑
                    Node Exporter
```

## 📚 Full Documentation
- Main: [README.md](README.md)
- Backend: [backend/README.md](backend/README.md)
- Deploy: [deploy/README.md](deploy/README.md)
- Implementation: [IMPLEMENTATION.md](IMPLEMENTATION.md)
