#!/bin/bash
# Deployment Script for Continumm Production Stack
# Builds and deploys the complete observability stack

set -e

echo ""
echo "=== Continumm Production Deployment ==="
echo ""

# Get git commit hash
if git rev-parse HEAD >/dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse HEAD)
    GIT_SHORT=$(git rev-parse --short HEAD)
    echo "Git commit: ${GIT_SHORT}"
else
    GIT_COMMIT="unknown"
    GIT_SHORT="unknown"
    echo "Warning: Git commit not available"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please update .env with your configuration"
fi

# Update GIT_COMMIT in .env
sed -i.bak "s/^GIT_COMMIT=.*/GIT_COMMIT=${GIT_COMMIT}/" .env
rm -f .env.bak

echo ""
echo "Building backend image..."
docker build --build-arg GIT_COMMIT="${GIT_COMMIT}" -t continumm-backend:${GIT_SHORT} -t continumm-backend:latest ../backend

echo ""
echo "Starting services..."
docker-compose down
docker-compose up -d

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services:"
echo "  Backend:    Internal only (via Nginx)"
echo "  Nginx:      http://localhost"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000 (admin/changeme)"
echo ""
echo "Check status:"
echo "  docker-compose ps"
echo "  docker-compose logs -f"
echo ""
echo "Test endpoints:"
echo "  curl http://localhost/health"
echo "  curl http://localhost/metrics"
echo "  curl http://localhost/version"
echo ""
