# Verification and Testing Script for Continumm Stack
# Tests all services and generates sample metrics

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Continumm Stack Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check if services are running
Write-Host "Checking services..." -ForegroundColor Green
$services = docker-compose ps --services --filter "status=running"

$requiredServices = @("backend", "nginx", "prometheus", "grafana", "node_exporter")
$allRunning = $true

foreach ($service in $requiredServices) {
    if ($services -contains $service) {
        Write-Host "  OK $service is running" -ForegroundColor Gray
    } else {
        Write-Host "  FAIL $service is not running" -ForegroundColor Red
        $allRunning = $false
    }
}

if (-not $allRunning) {
    Write-Host ""
    Write-Host "Not all services are running. Run: docker-compose up -d" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing endpoints..." -ForegroundColor Green

# Test backend via Nginx (port 80)
try {
    $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  OK Backend health check (via Nginx)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  FAIL Backend health check failed" -ForegroundColor Red
}

# Test version endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost/version" -UseBasicParsing
    $version = ($response.Content | ConvertFrom-Json)
    Write-Host "  OK Version endpoint (commit: $($version.commit.Substring(0,7)))" -ForegroundColor Gray
} catch {
    Write-Host "  FAIL Version endpoint failed" -ForegroundColor Red
}

# Test metrics endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost/metrics" -UseBasicParsing
    if ($response.Content -match "request_total") {
        Write-Host "  OK Metrics endpoint (Prometheus format)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  FAIL Metrics endpoint failed" -ForegroundColor Red
}

# Test Prometheus
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  OK Prometheus is healthy" -ForegroundColor Gray
    }
} catch {
    Write-Host "  FAIL Prometheus health check failed" -ForegroundColor Red
}

# Test Grafana
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  OK Grafana is healthy" -ForegroundColor Gray
    }
} catch {
    Write-Host "  FAIL Grafana health check failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "Verifying backend isolation..." -ForegroundColor Green

# Try to access backend directly (should fail)
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
    Write-Host "  FAIL Backend is exposed publicly (should not be!)" -ForegroundColor Red
} catch {
    Write-Host "  OK Backend is not publicly accessible (correct)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Generating test traffic for metrics..." -ForegroundColor Green

# Generate some traffic
$requests = 20
for ($i = 0; $i -lt $requests; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing | Out-Null
        Invoke-WebRequest -Uri "http://localhost/version" -UseBasicParsing | Out-Null
        Invoke-WebRequest -Uri "http://localhost/" -UseBasicParsing | Out-Null
    } catch {
        # Ignore errors
    }
    if ($i % 5 -eq 0) {
        Write-Host "  Generated $i requests..." -ForegroundColor Gray
    }
    Start-Sleep -Milliseconds 50
}
Write-Host "  Generated $requests requests" -ForegroundColor Gray

Write-Host ""
Write-Host "Checking Prometheus targets..." -ForegroundColor Green

Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets" -UseBasicParsing
    $targets = ($response.Content | ConvertFrom-Json).data.activeTargets
    
    $upTargets = $targets | Where-Object { $_.health -eq "up" }
    $downTargets = $targets | Where-Object { $_.health -ne "up" }
    
    foreach ($target in $upTargets) {
        Write-Host "  OK $($target.labels.job) is UP" -ForegroundColor Gray
    }
    
    foreach ($target in $downTargets) {
        Write-Host "  FAIL $($target.labels.job) is DOWN" -ForegroundColor Red
    }
} catch {
    Write-Host "  FAIL Could not fetch Prometheus targets" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  Backend (via Nginx): http://localhost" -ForegroundColor White
Write-Host "  Prometheus:          http://localhost:9090" -ForegroundColor White
Write-Host "  Grafana:             http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "View Grafana Dashboard:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:3000" -ForegroundColor White
Write-Host "  2. Login: admin / changeme" -ForegroundColor White
Write-Host "  3. Navigate to 'Dashboards' -> 'Continumm Backend - Production Metrics'" -ForegroundColor White
Write-Host ""
Write-Host "Check logs:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
