#!/bin/bash
# Build script for creating immutable Docker images with git SHA tagging

set -e

# Get git commit hash
GIT_COMMIT=$(git rev-parse HEAD)
GIT_SHORT=$(git rev-parse --short HEAD)

# Image name
IMAGE_NAME="continumm-backend"

echo "Building Docker image..."
echo "Git commit: ${GIT_COMMIT}"

# Build the image with git commit as build arg
docker build \
    --build-arg GIT_COMMIT="${GIT_COMMIT}" \
    -t "${IMAGE_NAME}:${GIT_SHORT}" \
    -t "${IMAGE_NAME}:latest" \
    -f Dockerfile \
    .

echo "✓ Image built successfully: ${IMAGE_NAME}:${GIT_SHORT}"
echo "✓ Also tagged as: ${IMAGE_NAME}:latest"
