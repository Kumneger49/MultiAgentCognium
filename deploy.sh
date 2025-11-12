#!/bin/bash

# Deployment script for RAG Agent
# This script helps deploy the container to a cloud VM

set -e

echo "🚀 RAG Agent Deployment Script"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "✅ Docker and docker-compose are installed"
echo ""

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY is not set"
    echo "   The container will start but RAG functionality may not work"
    echo ""
fi

if [ -z "$PERIGON_API_KEY" ]; then
    echo "⚠️  WARNING: PERIGON_API_KEY is not set"
    echo "   News fetching may not work"
    echo ""
fi

# Build the Docker image
echo "📦 Building Docker image..."
docker build -f processor/Dockerfile -t rag-agent-processor:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi

echo ""
echo "🎯 Starting container with docker-compose..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Container started successfully!"
    echo ""
    echo "📋 Container Status:"
    docker-compose ps
    echo ""
    echo "🌐 API is available at:"
    echo "   - Local: http://localhost:8000"
    echo "   - Network: http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    echo "📚 API Documentation:"
    echo "   - Swagger UI: http://localhost:8000/docs"
    echo "   - ReDoc: http://localhost:8000/redoc"
    echo ""
    echo "📊 View logs:"
    echo "   docker-compose logs -f rag-agent"
    echo ""
    echo "🛑 Stop container:"
    echo "   docker-compose down"
else
    echo "❌ Failed to start container"
    exit 1
fi

