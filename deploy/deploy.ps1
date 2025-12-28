# Deployment Script for Continumm Production Stack
# Builds and deploys the complete observability stack

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Continumm Production Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Get git commit hash
try {
    $GIT_COMMIT = git rev-parse HEAD
    $GIT_SHORT = git rev-parse --short HEAD
    Write-Host "Git commit: $GIT_SHORT" -ForegroundColor Green
} catch {
    $GIT_COMMIT = "unknown"
    $GIT_SHORT = "unknown"
    Write-Host "Warning: Git commit not available" -ForegroundColor Yellow
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Please update .env with your configuration" -ForegroundColor Yellow
}

# Update GIT_COMMIT in .env
$envContent = Get-Content ".env"
$envContent = $envContent -replace "^GIT_COMMIT=.*", "GIT_COMMIT=$GIT_COMMIT"
$envContent | Set-Content ".env"

Write-Host ""
Write-Host "Building backend image..." -ForegroundColor Green
docker build --build-arg GIT_COMMIT="$GIT_COMMIT" -t continumm-backend:$GIT_SHORT -t continumm-backend:latest ../backend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Green
docker-compose down
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor Green
Write-Host "  Backend:    Internal only (via Nginx)" -ForegroundColor Gray
Write-Host "  Nginx:      http://localhost" -ForegroundColor Gray
Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor Gray
Write-Host "  Grafana:    http://localhost:3000 (admin/changeme)" -ForegroundColor Gray
Write-Host ""
Write-Host "Check status:" -ForegroundColor Yellow
Write-Host "  docker-compose ps" -ForegroundColor White
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "Test endpoints:" -ForegroundColor Yellow
Write-Host "  curl http://localhost/health" -ForegroundColor White
Write-Host "  curl http://localhost/metrics" -ForegroundColor White
Write-Host "  curl http://localhost/version" -ForegroundColor White
Write-Host ""
