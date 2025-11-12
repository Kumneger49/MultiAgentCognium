#!/bin/bash
# Script to prepare files for DigitalOcean deployment

echo "📦 Preparing deployment package..."

cd /Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working

# Create tarball with necessary files
tar -czf rag-agent-deploy.tar.gz \
  processor/ \
  orchestrator/ \
  news_agent/ \
  cognium_codebase/ \
  email_sending_agent/ \
  client_based_recommendation/ \
  docker-compose.yml \
  requirements.txt \
  api.py \
  .dockerignore \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='rag_storage' \
  --exclude='cognium_codebase/output' \
  --exclude='cognium_codebase/rag_storage' \
  --exclude='*.pdf' \
  --exclude='*.json' \
  --exclude='*.txt' \
  --exclude='cognium_codebase/data/*.pdf' \
  2>/dev/null

if [ -f rag-agent-deploy.tar.gz ]; then
    echo "✅ Created rag-agent-deploy.tar.gz"
    echo "📊 Size: $(du -h rag-agent-deploy.tar.gz | cut -f1)"
    echo ""
    echo "Next step: Upload to your droplet:"
    echo "  scp rag-agent-deploy.tar.gz root@YOUR_DROPLET_IP:/root/"
else
    echo "❌ Failed to create deployment package"
    exit 1
fi
