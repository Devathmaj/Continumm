<![CDATA[# Nginx Reverse Proxy

Nginx serves as the **only public entry point** for the Continumm stack. All external traffic flows through Nginx before reaching the backend.

## Purpose

- Reverse proxy to the backend service on the internal Docker network
- Rate limiting (10 req/s per IP, burst 20)
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy)
- Health-aware routing with automatic failover (`max_fails=3, fail_timeout=30s`)
- Connection pooling (`keepalive 32`)
- Explicit timeout control (connect 5s, send/read 60s)
- Retry logic on 500/502/503 errors (max 2 tries, 10s total)

## Configuration

The Nginx config lives at `deploy/nginx/nginx.conf` and is mounted read-only into the container.

Key sections:
- **`upstream backend`** — Backend pool with health-aware routing and keepalive
- **`limit_req_zone`** — Per-IP rate limiting zone (10m shared memory)
- **`location /`** — Main proxy with rate limiting, buffering, retry logic
- **`location /health`** — Health check proxy (no rate limiting, fast timeout)
- **`location /nginx_status`** — Stub status restricted to internal network (`172.16.0.0/12`)

## Zero-Downtime Reload

See [NGINX.md](../NGINX.md) for the full operations guide including reload scripts and testing procedures.

```powershell
.\reload-nginx.ps1    # Windows
./reload-nginx.sh     # Linux/macOS
```

## Troubleshooting

| Status | Cause | Fix |
|--------|-------|-----|
| 502 | Backend is down or starting | `docker-compose logs backend` |
| 504 | Backend too slow | Increase `proxy_read_timeout` |
| 429 | Rate limit exceeded | Adjust `rate` and `burst` in config |
]]>
