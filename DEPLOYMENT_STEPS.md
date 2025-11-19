# Deployment Steps (DigitalOcean Droplet)

Comprehensive record of how we deployed the unified RAG Agent container to the production droplet and made the API available at `http://165.232.190.9:8000`.

---

## 1. Prerequisites
- DigitalOcean droplet (Ubuntu 22.04, 2 GB RAM)
- SSH access (`root@165.232.190.9`)
- Docker Engine + Docker Compose v2 installed on the droplet
- Local workspace containing the project (this repository)

> If Docker/Compose are missing, install them on the droplet:
```bash
apt-get update && apt-get install -y ca-certificates curl gnupg
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---

## 2. Local Preparation
1. **Ensure project is clean** and the unified API/processor container runs locally:
   ```bash
   docker compose up --build
   docker compose exec rag-agent curl -s http://localhost:8000
   ```
2. **Bundle deployment assets** using the helper script:
   ```bash
   ./prepare-deployment.sh
   ```
   This produces `rag-agent-deploy.tar.gz` containing:
   - Core services (`api.py`, `client_based_recommendation/`, `cognium_codebase/`, `orchestrator/`, etc.)
   - Docker artifacts (`processor/Dockerfile`, `docker-compose.yml`, `.dockerignore`, `requirements.txt`)
   - Excludes bulky caches and secrets

---

## 3. Transfer to Droplet
Upload the tarball via SCP:
```bash
scp rag-agent-deploy.tar.gz root@165.232.190.9:/root/
```
Alternatively use DigitalOcean’s web console if SCP is unavailable.

---

## 4. Provision on Droplet
1. **SSH into the droplet**
   ```bash
   ssh root@165.232.190.9
   ```
2. **Extract bundle**
   ```bash
   cd /root
   tar -xzf rag-agent-deploy.tar.gz
   ```
   All files restore under `/root/` (same layout as local repo root).
3. **Create `.env`** with production secrets:
   ```bash
   cat <<'ENV' > .env
   OPENAI_API_KEY="<your-openai-key>"
   PERIGON_API_KEY="<your-perigon-key>"
   ALLOWED_ORIGINS="*"           # tighten in prod
   API_KEY=""                    # empty disables auth for POST endpoint
   ENV
   ```
4. **Initialize `prety_recommendation.json`** to avoid empty-JSON errors:
   ```bash
   [ -f prety_recommendation.json ] || echo '[]' > prety_recommendation.json
   ```

---

## 5. Configure HTTPS with Caddy
1. **Create DNS record** for your domain pointing to the droplet IP (e.g., `api.example.com → 165.232.190.9`).
2. **Open ports 80/443** in any firewalls (`ufw allow 80/tcp 443/tcp`).
3. **Edit `Caddyfile`** to use your domain and contact email:
   ```
   {
       email admin@example.com
   }

   api.example.com {
       encode gzip zstd
       reverse_proxy rag-agent:8000
   }
   ```
   Caddy will request/renew TLS certificates automatically.

---

## 6. Build & Run Containers
1. **Build the unified image**
   ```bash
   docker build -t rag-agent-processor:latest -f processor/Dockerfile .
   ```
2. **Start services (FastAPI + Caddy)**
   ```bash
   docker compose up -d
   ```
3. **Open firewall (if UFW enabled)**
   ```bash
   ufw allow 8000/tcp
   ```
4. **Confirm status**
   ```bash
   docker compose ps
   docker logs rag-agent --tail 50
   curl -s http://localhost:8000/api/merged-news | jq '.count'
   ```

---

## 7. Post-Deployment Fixes
- The 2 GB droplet could not reparse PDFs (Docling/MinerU OOM). To work around this:
  1. Packaged local cache: `tar -czf rag_storage_cache.tar.gz rag_storage/`
  2. Uploaded to droplet and extracted into `/root/rag_storage/`
  3. Restarted container: `docker compose restart rag-agent`
  4. Regenerated recommendations successfully (32 entries)

- `POST /api/regenerate-recommendations` now works without an API key because `API_KEY` is empty (auth disabled).

---

## 8. Verification Checklist
- `GET https://api.example.com/api/merged-news` → returns categorized news
- `GET https://api.example.com/api/recommendations` → returns generated recommendations
- `POST https://api.example.com/api/regenerate-recommendations` → triggers pipeline, completes in ~3 minutes
- Local `frontend.html` can call the deployed API to view/trigger recommendations.

---

## 9. Future Improvements
- Add HTTPS termination (DigitalOcean Load Balancer, Caddy, etc.)
- Enable API key auth by setting a value in `.env`
- Move to higher-memory droplet or optimize PDF parsing if on-the-fly processing is required
- Automate deployment via CI/CD once repository lives on GitHub

---

_Last updated: 2025-11-11_
