# Nginx Reverse Proxy - Zero-Downtime Configuration

Production-ready Nginx configuration with health-aware routing and graceful reloads.

## 🎯 What This Proves

- ✅ **Zero-downtime reloads** - Configuration updates without dropping connections
- ✅ **Health-aware routing** - Automatic failover when backend is unhealthy
- ✅ **Explicit timeouts** - All timeout values clearly defined and tuned
- ✅ **Blast radius control** - Nginx isolates backend failures

## 🔧 Configuration Features

### Health-Aware Routing

```nginx
upstream backend {
    server backend:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

**How it works:**
1. Nginx monitors backend health via passive health checks
2. If 3 consecutive requests fail, backend is marked as down for 30 seconds
3. Traffic automatically stops going to failed backend
4. Backend is retried after timeout period
5. Traffic resumes when backend is healthy

### Explicit Timeouts

All timeout values are explicitly defined:

```nginx
# Connection timeout: establish connection to backend
proxy_connect_timeout 5s;

# Send timeout: between successive write operations
proxy_send_timeout 60s;

# Read timeout: between successive read operations  
proxy_read_timeout 60s;
```

**Why explicit timeouts matter:**
- Prevents requests from hanging indefinitely
- Controls blast radius of backend failures
- Predictable failure behavior
- Tuned for application characteristics

### Retry Logic

```nginx
# Retry on specific errors
proxy_next_upstream error timeout http_500 http_502 http_503;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 10s;
```

**Automatic retry when:**
- Connection error to backend
- Timeout waiting for backend
- Backend returns 500, 502, or 503
- Max 2 retry attempts
- Give up after 10 seconds total

### Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=20 nodelay;
```

**Protection:**
- 10 requests/second sustained rate per IP
- Burst of 20 additional requests allowed
- Excess requests rejected with 429 (Too Many Requests)

### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

## 🔄 Zero-Downtime Reload

### How Graceful Reload Works

```
1. Test Configuration
   ├─→ nginx -t validates syntax
   └─→ Exit if invalid

2. Send Reload Signal
   ├─→ nginx -s reload (or kill -HUP)
   └─→ Master process receives signal

3. Master Process Actions
   ├─→ Parse new configuration
   ├─→ Spawn new worker processes with new config
   └─→ Signal old workers to shut down gracefully

4. Old Workers Graceful Shutdown
   ├─→ Stop accepting new connections
   ├─→ Finish processing existing requests
   ├─→ Close connections when complete
   └─→ Exit

5. New Workers Take Over
   ├─→ Accept all new connections
   ├─→ Use new configuration
   └─→ Zero requests dropped
```

### Reload Script

**Windows:**
```powershell
.\reload-nginx.ps1
```

**Linux/Mac:**
```bash
./reload-nginx.sh
```

**What the script does:**
1. Validates configuration before reloading
2. Exits if configuration is invalid (prevents breaking Nginx)
3. Performs graceful reload
4. Verifies Nginx is responding after reload

## 🧪 Testing Zero-Downtime

### Test Scenario: Reload Under Load

**Terminal 1: Generate continuous traffic**
```powershell
while ($true) {
    $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing
    Write-Host "Status: $($response.StatusCode) - $(Get-Date -Format 'HH:mm:ss.fff')"
    Start-Sleep -Milliseconds 100
}
```

**Terminal 2: Reload Nginx**
```powershell
cd deploy
.\reload-nginx.ps1
```

**Expected Result:**
- All requests return 200 OK
- No 502/503 errors during reload
- No dropped connections
- Reload completes in < 1 second

### Test Scenario: Backend Failure

**Simulate backend failure:**
```powershell
# Stop backend
docker-compose stop backend

# Watch Nginx handle it
curl http://localhost/health  # Should return 502/503 quickly
```

**Expected Behavior:**
- Nginx returns 502/504 within timeout period (5s)
- No hanging requests
- Error logged properly
- Service recovers when backend restarts

**Restart backend:**
```powershell
docker-compose start backend
Start-Sleep -Seconds 5
curl http://localhost/health  # Should return 200 OK
```

### Test Scenario: Health-Aware Routing

This requires multiple backend instances (see Multi-Backend Setup below).

## 📊 Monitoring Nginx

### Nginx Status Endpoint

```bash
# Restricted to internal network
curl http://localhost/nginx_status
```

**Metrics:**
- Active connections
- Requests per second
- Reading/Writing/Waiting connections

### Nginx Logs

```bash
# Access logs
docker-compose logs nginx | grep "GET\|POST"

# Error logs
docker-compose logs nginx | grep "error"

# Tail logs
docker-compose logs -f nginx
```

### Connection States

```bash
# Inside Nginx container
docker-compose exec nginx sh

# Connection statistics
netstat -an | grep :80 | wc -l       # Total connections
netstat -an | grep :80 | grep ESTABLISHED | wc -l  # Established
```

## ⚙️ Configuration Tuning

### For High Traffic

Increase worker connections and keepalive:

```nginx
# nginx.conf (main context, not included in our config)
worker_processes auto;
worker_connections 4096;

# upstream block
keepalive 128;
keepalive_requests 1000;
```

### For Slow Backends

Increase timeouts:

```nginx
proxy_connect_timeout 10s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### For Fast Backends

Decrease timeouts for faster failure detection:

```nginx
proxy_connect_timeout 2s;
proxy_read_timeout 30s;
```

## 🔍 Troubleshooting

### 502 Bad Gateway

**Causes:**
- Backend is down
- Backend is starting up
- Connection timeout

**Check:**
```bash
# Is backend running?
docker-compose ps backend

# Can Nginx reach backend?
docker-compose exec nginx wget -O- http://backend:8000/health

# Backend logs
docker-compose logs backend
```

### 504 Gateway Timeout

**Causes:**
- Backend is responding slowly
- Timeout too short for request type

**Fix:**
- Increase `proxy_read_timeout`
- Optimize backend performance
- Check backend logs for slow operations

### Configuration Test Failed

**Common errors:**
- Syntax error in config
- Invalid directive
- Missing semicolon

**Debug:**
```bash
# Test config
docker-compose exec nginx nginx -t

# Check for typos
docker-compose exec nginx cat /etc/nginx/conf.d/default.conf
```

## 🎯 Best Practices

### DO:
- ✅ Always test config before reloading (`nginx -t`)
- ✅ Use explicit timeout values
- ✅ Set up rate limiting
- ✅ Monitor Nginx logs
- ✅ Use health checks
- ✅ Configure proper buffer sizes

### DON'T:
- ❌ Reload without testing
- ❌ Use default timeout values
- ❌ Expose backend directly
- ❌ Ignore error logs
- ❌ Skip monitoring setup

## 🚀 Advanced: Multi-Backend Setup

For true zero-downtime deploys with multiple backends:

```nginx
upstream backend {
    least_conn;  # Load balance by least connections
    
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    server backend-3:8000 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}
```

**Deploy process:**
1. Deploy to backend-1, Nginx stops routing to it
2. Wait for health check to pass, traffic resumes
3. Repeat for backend-2 and backend-3
4. Zero total downtime

## 📚 Reference

### Nginx Reload Signals

- `nginx -s reload` - Graceful reload
- `nginx -s stop` - Fast shutdown
- `nginx -s quit` - Graceful shutdown
- `nginx -s reopen` - Reopen log files

### Docker Compose Nginx Commands

```bash
# Reload configuration
docker-compose exec nginx nginx -s reload

# Test configuration
docker-compose exec nginx nginx -t

# View running config
docker-compose exec nginx cat /etc/nginx/conf.d/default.conf

# Check processes
docker-compose exec nginx ps aux

# Restart container (not graceful)
docker-compose restart nginx
```

---

**Nginx exists to control blast radius, not routing tricks.**

Configuration file: [deploy/nginx/nginx.conf](nginx.conf)
Reload script: [deploy/reload-nginx.ps1](reload-nginx.ps1)
