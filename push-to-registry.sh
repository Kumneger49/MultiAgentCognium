#!/bin/bash

# Script to build and push Docker image to DigitalOcean Container Registry

set -e

# Configuration - UPDATE THESE
REGISTRY_NAME="rag-agent-registry"  # Your registry name
IMAGE_NAME="rag-agent"               # Image name in registry
VERSION_TAG="v1.0.0"                 # Version tag (update for each release)

# Full image paths
REGISTRY_URL="registry.digitalocean.com/${REGISTRY_NAME}/${IMAGE_NAME}"
LATEST_TAG="${REGISTRY_URL}:latest"
VERSION_TAG_FULL="${REGISTRY_URL}:${VERSION_TAG}"

echo "🚀 Building and Pushing to DigitalOcean Container Registry"
echo "============================================================"
echo ""
echo "Registry: ${REGISTRY_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Version: ${VERSION_TAG}"
echo ""

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl is not installed"
    echo "   Install: brew install doctl (macOS) or download from DigitalOcean"
    exit 1
fi

# Check if logged in to registry
echo "🔐 Checking registry authentication..."
if ! doctl registry login &> /dev/null; then
    echo "⚠️  Not logged in to registry"
    echo "   Running: doctl registry login"
    doctl registry login
fi

# Build the image
echo ""
echo "📦 Building Docker image..."
docker build -f processor/Dockerfile -t rag-agent-processor:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Image built successfully"
echo ""

# Tag the image
echo "🏷️  Tagging image..."
docker tag rag-agent-processor:latest ${LATEST_TAG}
docker tag rag-agent-processor:latest ${VERSION_TAG_FULL}

echo "✅ Tagged as:"
echo "   - ${LATEST_TAG}"
echo "   - ${VERSION_TAG_FULL}"
echo ""

# Push to registry
echo "⬆️  Pushing to registry (this may take a few minutes)..."
echo "   Pushing latest tag..."
docker push ${LATEST_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Failed to push latest tag"
    exit 1
fi

echo "   Pushing version tag..."
docker push ${VERSION_TAG_FULL}

if [ $? -ne 0 ]; then
    echo "❌ Failed to push version tag"
    exit 1
fi

echo ""
echo "✅ Successfully pushed to registry!"
echo ""
echo "📋 Image tags in registry:"
doctl registry repository list-tags ${REGISTRY_NAME}/${IMAGE_NAME}
echo ""
echo "🎯 Next steps:"
echo "   1. SSH into your droplet"
echo "   2. Run: docker pull ${LATEST_TAG}"
echo "   3. Update docker-compose.yml to use: ${LATEST_TAG}"
echo "   4. Run: docker-compose up -d"
echo ""

