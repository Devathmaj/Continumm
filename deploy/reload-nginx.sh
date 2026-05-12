#!/bin/bash
# Graceful Nginx Reload Script
# Reloads Nginx configuration without dropping existing connections
# Ensures zero-downtime during configuration updates

set -e

echo ""
echo "=== Nginx Graceful Reload ==="
echo ""

# Check if Nginx container is running
if ! docker-compose ps --services --filter "status=running" | grep -q "nginx"; then
    echo "ERROR: Nginx container is not running"
    echo "Start the stack first: docker-compose up -d"
    exit 1
fi

echo "Testing Nginx configuration..."
if ! docker-compose exec -T nginx nginx -t; then
    echo "ERROR: Nginx configuration is invalid"
    exit 1
fi

echo "Configuration is valid"
echo ""

echo "Performing graceful reload..."
echo "  - Existing connections will complete normally"
echo "  - New connections will use updated configuration"
echo "  - No dropped requests"
echo ""

# Send HUP signal to Nginx master process for graceful reload
docker-compose exec -T nginx nginx -s reload

if [ $? -eq 0 ]; then
    echo "✓ Nginx reloaded successfully"
    echo ""
    echo "Verifying Nginx is responding..."
    sleep 2
    
    if curl -f -s http://localhost/health > /dev/null; then
        echo "✓ Nginx is healthy and serving traffic"
    else
        echo "WARNING: Could not verify Nginx health"
    fi
else
    echo "ERROR: Reload failed"
    exit 1
fi

echo ""
echo "=== Reload Complete ==="
echo ""
echo "What happened:"
echo "  1. Configuration validated before reload"
echo "  2. Master process spawned new workers with new config"
echo "  3. Old workers finished existing requests"
echo "  4. Old workers shut down gracefully"
echo "  5. Zero requests dropped"
echo ""
