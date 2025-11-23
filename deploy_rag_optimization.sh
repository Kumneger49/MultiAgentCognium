#!/bin/bash
# Deploy RAG optimization files to DigitalOcean droplet
# This script transfers the updated files that implement RAG instance reuse

DROPLET_IP="165.232.190.9"
DROPLET_USER="root"
DROPLET_PATH="/root"

echo "=========================================="
echo "Deploying RAG Optimization Files"
echo "=========================================="
echo ""

# Files to transfer
FILES=(
    "cognium_codebase/main.py"
    "client_based_recommendation/news_pipeline.py"
)

echo "Transferring files to droplet..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  → Transferring $file..."
        scp "$file" "${DROPLET_USER}@${DROPLET_IP}:${DROPLET_PATH}/$(dirname "$file")/"
        if [ $? -eq 0 ]; then
            echo "    ✓ Success"
        else
            echo "    ✗ Failed"
            exit 1
        fi
    else
        echo "  ✗ File not found: $file"
        exit 1
    fi
done

echo ""
echo "=========================================="
echo "Files transferred successfully!"
echo "=========================================="
echo ""
echo "Next steps on the droplet:"
echo "  1. Restart the container:"
echo "     docker compose restart rag-agent"
echo ""
echo "  2. Or force recreate (if needed):"
echo "     docker compose up -d --force-recreate rag-agent"
echo ""
echo "  3. Monitor logs:"
echo "     docker compose logs -f rag-agent"
echo ""

