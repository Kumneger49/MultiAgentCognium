# Cognium RAG Agent API

Multi-service financial news analysis and client recommendation system with REST API, deployed to DigitalOcean with Docker and HTTPS.

## Overview

This system:
1. **Fetches financial news** from Yahoo Finance RSS and Perigon API
2. **Scores news articles** for relevance and sentiment using LLM
3. **Generates client recommendations** using RAG (Retrieval-Augmented Generation) against client portfolio PDFs
4. **Serves recommendations via REST API** with rotation system for multiple clients
5. **Deployed on DigitalOcean** with Docker, Caddy (HTTPS), and automatic certificate management

---

## Architecture

### Unified Container Approach

The system uses a **single Docker container** that serves both:
- **FastAPI REST API** (endpoints for recommendations)
- **Processing capabilities** (news fetching, scoring, RAG generation)

This eliminates inter-container communication issues and simplifies deployment.

### Recommendation Rotation System

- **5 pre-generated recommendation sets** (generated locally)
- **Per-client rotation** - each client independently cycles through sets 1-5
- **GET endpoint** - Returns current set (doesn't advance rotation)
- **POST endpoint** - Waits 5 seconds, advances to next set, returns new recommendations

---

## Project Structure

```
working/
├── api.py                              # Main FastAPI application (unified API + processing)
├── rotation_manager.py                  # Manages per-client rotation through recommendation sets
├── docker-compose.yml                  # Docker Compose configuration
├── Caddyfile                           # Caddy reverse proxy config (HTTPS)
├── processor/
│   └── Dockerfile                      # Docker image for unified container
│
├── cognium_codebase/                   # RAGAnything core system
│   ├── main.py                        # RAG initialization and query functions
│   ├── data/                          # Input PDFs (client portfolios)
│   └── rag_storage/                   # Persistent knowledge graph and caches
│
├── client_based_recommendation/         # Recommendation generation
│   ├── news_pipeline.py               # Full pipeline: fetch → score → merge → generate
│   ├── client_level_rec.py            # Client-level recommendation generation
│   └── merged_news.json               # Categorized news output
│
├── news_agent/                         # News fetching service
│   ├── main.py                        # Yahoo Finance RSS fetcher
│   └── MultipleNewsSources.py         # Perigon API multi-source fetcher
│
├── orchestrator/                       # CLI pipeline orchestrator
│   └── main.py                        # End-to-end pipeline orchestrator
│
├── email_sending_agent/                # Email service (optional)
│   └── agent.py                       # Gmail API email sending
│
├── recommendation_sets/                 # Pre-generated recommendation sets (1-5)
│   ├── recommendations_set_1.json
│   ├── recommendations_set_2.json
│   ├── recommendations_set_3.json
│   ├── recommendations_set_4.json
│   ├── recommendations_set_5.json
│   └── generation_metadata.json
│
├── generate_recommendation_sets.py     # Script to generate 5 sets locally
├── prepare-deployment.sh              # Script to bundle files for deployment
└── requirements.txt                    # Python dependencies
```

---

## Prerequisites

- Python 3.11+ (for local development)
- Docker and Docker Compose (for deployment)
- OpenAI API key (`OPENAI_API_KEY`)
- Perigon API key (`PERIGON_API_KEY`) - optional, for additional news sources
- DigitalOcean droplet (for production deployment)
- Domain name (for HTTPS with Caddy)

---

## Local Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file or export in your shell:

```bash
OPENAI_API_KEY=your_openai_key
PERIGON_API_KEY=your_perigon_key  # Optional
RAG_PARSER=mineru                 # Optional: mineru or docling (default: auto-detect)
```

### 3. Generate Recommendation Sets (Local)

Generate 5 recommendation sets locally (takes ~1-2 hours with 5-minute intervals):

```bash
python generate_recommendation_sets.py
```

This will:
- Run the full pipeline 5 times (fetch → score → merge → generate)
- Wait 5 minutes between each run (for fresh news)
- Save each set to `recommendation_sets/recommendations_set_{1-5}.json`

---

## API Endpoints

The API is served from `api.py` at the root level.

### Base URL
- **Local**: `http://localhost:8000`
- **Production**: `https://api.cognium.xyz` (or your domain)

### Endpoints

#### `GET /`
Returns API information and available endpoints.

#### `GET /api/merged-news`
Retrieve categorized and merged news by ticker.

#### `GET /api/recommendations`
Retrieve all recommendations (from `prety_recommendation.json`).

#### `GET /api/recommendations/client/{client_id}`
Get recommendations for a specific client (current set, **does not advance rotation**).

**Response:**
```json
{
  "status": "success",
  "client_id": "user_123",
  "set_number": 1,
  "data": [...recommendations...],
  "count": 45
}
```

#### `POST /api/regenerate-recommendations/client/{client_id}`
Advance client to next recommendation set (waits 5 seconds, then returns new set).

**Response:**
```json
{
  "status": "success",
  "client_id": "user_123",
  "set_number": 2,
  "message": "Recommendations updated successfully",
  "data": [...recommendations...],
  "count": 43
}
```

**Note:** This is the "regenerate" button endpoint. It rotates through pre-generated sets (1 → 2 → 3 → 4 → 5 → 1).

#### `POST /api/regenerate-recommendations`
Trigger actual regeneration with fresh news (fetches, scores, merges, generates).

**Note:** This runs the full pipeline and takes 5-10 minutes. Requires API key if configured.

#### `GET /api/generate-client-id`
Generate a new client ID (UUID) for users who don't have one.

**Response:**
```json
{
  "status": "success",
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Use this client_id in /api/recommendations/client/{client_id}..."
}
```

#### `GET /docs`
Interactive API documentation (Swagger UI).

#### `GET /redoc`
Alternative API documentation (ReDoc).

---

## Local Development

### Run API Locally

```bash
# From project root
uvicorn api:app --reload --port 8000
```

### Test Endpoints

```bash
# Get recommendations for a client
curl http://localhost:8000/api/recommendations/client/user_123

# Advance to next set (waits 5 seconds)
curl -X POST http://localhost:8000/api/regenerate-recommendations/client/user_123

# Generate a new client ID
curl http://localhost:8000/api/generate-client-id
```

---

## Deployment to DigitalOcean

### Prerequisites

1. **DigitalOcean Droplet** (Ubuntu 22.04 with Docker)
2. **Domain name** (for HTTPS with Caddy)
3. **DNS A record** pointing to droplet IP

### Quick Deployment Steps

1. **Prepare deployment package:**
   ```bash
   ./prepare-deployment.sh
   ```

2. **Upload to droplet:**
   ```bash
   scp rag-agent-deploy.tar.gz root@YOUR_DROPLET_IP:/root/
   scp api.py root@YOUR_DROPLET_IP:/root/
   scp rotation_manager.py root@YOUR_DROPLET_IP:/root/
   scp docker-compose.yml root@YOUR_DROPLET_IP:/root/
   scp Caddyfile root@YOUR_DROPLET_IP:/root/
   scp -r recommendation_sets/ root@YOUR_DROPLET_IP:/root/
   ```

3. **On droplet, extract and setup:**
   ```bash
   cd /root
   tar -xzf rag-agent-deploy.tar.gz
   
   # Set environment variables
   export OPENAI_API_KEY=your_key
   export PERIGON_API_KEY=your_key
   
   # Build Docker image
   cd processor
   docker build -t rag-agent-processor:latest .
   cd ..
   
   # Start services
   docker compose up -d
   ```

4. **Configure DNS:**
   - Add A record: `api.yourdomain.com` → droplet IP
   - Update `Caddyfile` with your domain

5. **Restart Caddy:**
   ```bash
   docker compose restart caddy
   ```

### Verify Deployment

```bash
# Check containers
docker compose ps

# Check logs
docker compose logs rag-agent

# Test endpoint
curl https://api.yourdomain.com/api/recommendations/client/user_123
```

For detailed deployment instructions, see `DEPLOYMENT_STEPS.md`.

---

## How It Works

### Recommendation Generation Flow

1. **Local Generation** (on developer machine):
   ```bash
   python generate_recommendation_sets.py
   ```
   - Runs full pipeline 5 times with intervals
   - Each run: Fetch news → Score → Merge → Generate recommendations
   - Saves to `recommendation_sets/recommendations_set_{1-5}.json`

2. **Upload to Cloud**:
   - Upload `recommendation_sets/` directory to droplet
   - Mount in `docker-compose.yml`

3. **Client Rotation**:
   - Each client starts at set 1
   - GET endpoint returns current set (doesn't advance)
   - POST endpoint advances to next set (1 → 2 → 3 → 4 → 5 → 1)
   - Each client rotates independently

### News Pipeline

The `news_pipeline.py` consolidates the entire process:

1. **Fetch News** (`get_news_for_symbols`)
   - Yahoo Finance RSS
   - Perigon API (if configured)

2. **Score News** (`score_news_with_llm`)
   - Relevance score (0-1)
   - Sentiment score (-1 to 1)

3. **Categorize & Merge** (`categorize_and_merge_news`)
   - Groups by ticker
   - Categorizes by topic

4. **Generate Recommendations** (`generate_recommendations`)
   - Uses RAG system to generate client-specific recommendations
   - Processes in batches to manage memory
   - Reuses RAG instance for efficiency

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | Yes |
| `PERIGON_API_KEY` | Perigon API key for news | Optional |
| `RAG_PARSER` | Parser: `mineru` or `docling` | Optional (auto-detect) |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | Optional (default: `*`) |
| `API_KEY` | API key for POST endpoints | Optional |

### Docker Compose

Key configuration in `docker-compose.yml`:
- **Ports**: 8000 (API), 80/443 (Caddy)
- **Volumes**: Code directories, recommendation sets, RAG storage
- **Environment**: API keys, CORS, parser selection

### Caddy (HTTPS)

Caddy automatically:
- Obtains Let's Encrypt certificates
- Renews certificates automatically
- Handles HTTP → HTTPS redirects

Configuration in `Caddyfile`:
```
api.yourdomain.com {
    reverse_proxy rag-agent:8000
}
```

---

## Key Components

### `api.py`
Main FastAPI application with all endpoints. Handles:
- Client recommendation rotation
- News pipeline triggering
- CORS and API key authentication

### `rotation_manager.py`
Manages per-client rotation state:
- Tracks which set each client is on
- Persists state in `rotation_state.json`
- Handles new clients (start at set 1)

### `client_based_recommendation/news_pipeline.py`
Consolidated news processing pipeline:
- `run_full_pipeline()` - Complete flow: fetch → score → merge → generate
- Batch processing for memory efficiency
- RAG instance reuse for performance

### `cognium_codebase/main.py`
RAGAnything integration:
- `init_rag(file_path)` - Initialize RAG instance
- `query_rag(rag_instance, query)` - Query RAG system
- `main(query, file_path)` - Backward compatibility wrapper

---

## Data Storage

### Critical (Must Preserve)
- **`rag_storage/`** - Knowledge graph, embeddings, caches (~50-100MB)
- **`recommendation_sets/`** - Pre-generated recommendation sets
- **`rotation_state.json`** - Per-client rotation state

### Output Files
- **`prety_recommendation.json`** - Latest generated recommendations
- **`client_based_recommendation/merged_news.json`** - Categorized news
- **`orchestrator/prety_news.json`** - Scored news cache

### Ephemeral (Can Regenerate)
- **`cognium_codebase/output/`** - Parsed document outputs
- **`recommendation_sets/generation_metadata.json`** - Generation logs

---

## Troubleshooting

### API Issues

**404 on endpoints:**
- Check if `api.py` and `rotation_manager.py` are uploaded to droplet
- Verify they're mounted in `docker-compose.yml`
- Restart container: `docker compose restart rag-agent`

**Same recommendations every time:**
- Use POST endpoint to advance rotation (GET doesn't advance)
- Check `rotation_state.json` exists and is writable

**Empty recommendations:**
- Verify `recommendation_sets/` directory is mounted
- Check all 5 JSON files exist
- Verify file permissions

### RAG Issues

**Parser errors:**
- Set `RAG_PARSER=mineru` in environment (more reliable)
- Ensure parser is installed: `pip install mineru` or `pip install docling`

**Memory issues (OOM):**
- System uses instance reuse to minimize memory
- For local generation, memory is not a constraint
- Cloud deployment uses pre-generated sets (no generation on cloud)

### Deployment Issues

**HTTPS not working:**
- Verify DNS A record points to droplet
- Check Caddy logs: `docker compose logs caddy`
- Ensure ports 80/443 are open in firewall

**Container won't start:**
- Check logs: `docker compose logs rag-agent`
- Verify environment variables are set
- Check file permissions on mounted volumes

---

## Development Workflow

### 1. Generate Recommendation Sets Locally

```bash
# Generate 5 sets with 5-minute intervals
python generate_recommendation_sets.py
```

### 2. Test Locally

  ```bash
# Start API
uvicorn api:app --reload

# Test rotation
curl http://localhost:8000/api/recommendations/client/test_user
curl -X POST http://localhost:8000/api/regenerate-recommendations/client/test_user
```

### 3. Deploy to Cloud

  ```bash
# Prepare and upload
./prepare-deployment.sh
scp rag-agent-deploy.tar.gz root@DROPLET_IP:/root/
# ... (upload other files)

# On droplet: build and start
docker compose up -d
```

### 4. Update Recommendation Sets

When you generate new sets locally:
  ```bash
# Upload new sets
scp -r recommendation_sets/ root@DROPLET_IP:/root/
docker compose restart rag-agent
```

---

## Security

- **API Key Authentication**: Optional for POST endpoints (set `API_KEY` env var)
- **CORS**: Configurable via `ALLOWED_ORIGINS` (default: `*` for development)
- **HTTPS**: Automatic via Caddy with Let's Encrypt
- **Environment Variables**: Never commit API keys or secrets

---

## Future Improvements

- [ ] Add authentication/authorization for client endpoints
- [ ] Implement rate limiting
- [ ] Add monitoring and logging
- [ ] Support for more recommendation sets
- [ ] Background job queue for regeneration
- [ ] Database for rotation state (instead of JSON file)
- [ ] Health check endpoints
- [ ] Metrics and analytics

---

## License

No license file included. Add a license of your choice if sharing or publishing.

---

## Support

For deployment issues, see `DEPLOYMENT_STEPS.md`.  
For memory optimization details, see `MEMORY_ANALYSIS.md`.
