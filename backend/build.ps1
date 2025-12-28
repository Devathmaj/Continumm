# PowerShell build script for creating immutable Docker images with git SHA tagging

$ErrorActionPreference = "Stop"

# Get git commit hash
$GIT_COMMIT = git rev-parse HEAD
$GIT_SHORT = git rev-parse --short HEAD

# Image name
$IMAGE_NAME = "continumm-backend"

Write-Host "Building Docker image..." -ForegroundColor Green
Write-Host "Git commit: $GIT_COMMIT" -ForegroundColor Cyan

# Build the image with git commit as build arg
docker build `
    --build-arg GIT_COMMIT="$GIT_COMMIT" `
    -t "${IMAGE_NAME}:${GIT_SHORT}" `
    -t "${IMAGE_NAME}:latest" `
    -f Dockerfile `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Image built successfully: ${IMAGE_NAME}:${GIT_SHORT}" -ForegroundColor Green
    Write-Host "✓ Also tagged as: ${IMAGE_NAME}:latest" -ForegroundColor Green
} else {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
