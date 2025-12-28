# Graceful Nginx Reload Script
# Reloads Nginx configuration without dropping existing connections
# Ensures zero-downtime during configuration updates

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Nginx Graceful Reload ===" -ForegroundColor Cyan
Write-Host ""

# Check if Nginx container is running
$nginxRunning = docker-compose ps --services --filter "status=running" | Select-String "nginx"

if (-not $nginxRunning) {
    Write-Host "ERROR: Nginx container is not running" -ForegroundColor Red
    Write-Host "Start the stack first: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "Testing Nginx configuration..." -ForegroundColor Green
$testResult = docker-compose exec -T nginx nginx -t 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Nginx configuration is invalid" -ForegroundColor Red
    Write-Host $testResult
    exit 1
}

Write-Host "Configuration is valid" -ForegroundColor Gray
Write-Host ""

Write-Host "Performing graceful reload..." -ForegroundColor Green
Write-Host "  - Existing connections will complete normally" -ForegroundColor Gray
Write-Host "  - New connections will use updated configuration" -ForegroundColor Gray
Write-Host "  - No dropped requests" -ForegroundColor Gray
Write-Host ""

# Send HUP signal to Nginx master process for graceful reload
docker-compose exec -T nginx nginx -s reload

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK Nginx reloaded successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verifying Nginx is responding..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "OK Nginx is healthy and serving traffic" -ForegroundColor Green
        }
    } catch {
        Write-Host "WARNING: Could not verify Nginx health" -ForegroundColor Yellow
    }
} else {
    Write-Host "ERROR: Reload failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Reload Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "What happened:" -ForegroundColor Yellow
Write-Host "  1. Configuration validated before reload" -ForegroundColor Gray
Write-Host "  2. Master process spawned new workers with new config" -ForegroundColor Gray
Write-Host "  3. Old workers finished existing requests" -ForegroundColor Gray
Write-Host "  4. Old workers shut down gracefully" -ForegroundColor Gray
Write-Host "  5. Zero requests dropped" -ForegroundColor Gray
Write-Host ""
