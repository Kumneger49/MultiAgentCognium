## Cognium RAG Agents

Multi-service financial news analysis and client recommendation system with REST API.

### Workflows

**1. CLI Pipeline (Orchestrator):**
- Fetch recent news per ticker/index (Perigon API / Yahoo Finance RSS)
- Score each news item (relevance and sentiment) with OpenAI via LangChain
- Run a RAG pipeline against a client-portfolio PDF to produce per-client notes grouped by ticker
- Email managers consolidated updates (one per manager) via Gmail API

**2. Client-Based Recommendations (Alternative Flow):**
- Categorize and merge news by ticker and topic
- Generate client-level recommendations based on categorized news and portfolios
- Filter by relevance score and sentiment

**3. REST API:**
- FastAPI service exposing endpoints for accessing processed news and recommendations

### Project Structure

```
working/
├── requirements.txt                    # Root-level dependencies (all services)
│
├── cognium_codebase/                   # RAGAnything core system
│   ├── main.py                        # Async RAG ingest/query function
│   ├── streamlit_app.py               # Streamlit UI (optional)
│   ├── requirements.txt               # Core RAG dependencies
│   ├── data/                          # Input PDFs (client portfolios, reports)
│   ├── rag_storage/                   # Persistent knowledge store (51MB+)
│   │   ├── graph_chunk_entity_relation.graphml
│   │   ├── kv_store_*.json            # Caches, entities, relations
│   │   └── vdb_*.json                 # Vector database embeddings
│   └── output/                        # Parsed document outputs (ephemeral, 181MB)
│
├── news_agent/                         # News fetching service
│   ├── main.py                        # Yahoo Finance RSS fetcher
│   └── MultipleNewsSources.py         # Perigon API multi-source fetcher
│
├── orchestrator/                       # Main CLI pipeline orchestrator
│   ├── main.py                        # End-to-end pipeline: news → score → RAG → email
│   ├── prety_news.json                # Scored news cache
│   ├── output.txt                     # RAG summaries log
│   └── email_output.txt               # Email dispatch logs
│
├── client_based_recommendation/         # Alternative recommendation flow
│   ├── catagorizeNews.py              # Categorize and merge news by ticker/topic
│   ├── client_level_rec.py            # Generate client-level recommendations
│   ├── merged_news.json               # Categorized news output (used by API)
│   └── prety_news.json                # Input: scored news
│
├── email_sending_agent/                # Email service
│   ├── agent.py                       # LangChain agent for email generation
│   ├── main.py                        # Gmail API wrapper
│   ├── credentials.json               # Google OAuth credentials (not in repo)
│   └── token.json                     # OAuth token (generated on first run)
│
└── fast_api/                          # REST API service
    ├── main.py                        # FastAPI application
    └── supabase_storage.py            # Optional Supabase integration

---

### Prerequisites

- Python 3.11.9 or newer
- An OpenAI API key (`OPENAI_API_KEY`)
- For email sending: Google API OAuth credentials (`email_sending_agent/credentials.json`)

---

### Setup (once)

```bash
python3 -m venv venv
source venv/bin/activate
python -V   # should be 3.11.9 or newer

# Install all dependencies from root requirements.txt
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

# Additional email dependencies (if not in requirements.txt)
python -m pip install google-auth google-auth-oauthlib google-api-python-client
```

Create a `.env` file at the repo root (and/or export in your shell):

```bash
OPENAI_API_KEY=your_openai_key
PERIGON_API_KEY=your_perigon_key  # Optional, for MultipleNewsSources
RAG_PARSER=docling                # Optional: docling or mineru (default: auto-detect)
```

These env vars are read by the components via `python-dotenv`.

---

### Component Overview

#### `cognium_codebase/` — RAGAnything Core System
- **Purpose**: Document parsing, knowledge graph construction, and RAG queries
- **Key Files**:
  - `main.py` — async `ragmain(query, file_path)` function used by orchestrator and client recommendations
  - `streamlit_app.py` — Optional Streamlit UI for document upload and querying
- **Storage**:
  - `rag_storage/` — **CRITICAL**: Persistent knowledge graph, embeddings, and caches (~51MB)
  - `output/` — Ephemeral parsed document outputs (~181MB, can be regenerated)
  - `data/` — Input PDFs (client portfolios, financial reports)

#### `news_agent/` — News Fetching Service
- **Purpose**: Fetch financial news from multiple sources
- **Key Files**:
  - `main.py` — Yahoo Finance RSS fetcher (no API key required)
  - `MultipleNewsSources.py` — Perigon API multi-source fetcher (requires PERIGON_API_KEY)
- **Output**: Returns dict `{ticker: [{date, title, summary, link, source, ...}]}`

#### `orchestrator/` — Main CLI Pipeline
- **Purpose**: End-to-end orchestration of news → scoring → RAG → email
- **Key Files**:
  - `main.py` — Main pipeline orchestrator
- **Workflow**:
  1. Loads cached scored news from `prety_news.json` (or fetches + scores if missing)
  2. Builds RAG prompt with scored news
  3. Calls RAG system to generate client recommendations
  4. Sends consolidated emails to managers via email agent
- **Output Files**:
  - `prety_news.json` — Scored news cache (JSON format)
  - `output.txt` — RAG summaries log
  - `email_output.txt` — Email dispatch logs

#### `client_based_recommendation/` — Alternative Recommendation Flow
- **Purpose**: Categorize news and generate client-level recommendations
- **Key Files**:
  - `catagorizeNews.py` — Groups news by ticker, categorizes by topic, includes relevance/sentiment scores
  - `client_level_rec.py` — Generates client-specific recommendations using RAG system
- **Workflow**:
  1. Reads scored news from `prety_news.json`
  2. Filters news with `relevance_score = 0`
  3. Groups by ticker and categorizes by topic using LLM
  4. Generates client recommendations in batches
- **Output Files**:
  - `merged_news.json` — Categorized news (used by FastAPI endpoint)
  - `prety_recommendation.txt` — Client recommendations output

#### `email_sending_agent/` — Email Service
- **Purpose**: Send emails to managers via Gmail API
- **Key Files**:
  - `agent.py` — LangChain agent that extracts manager emails from RAG output and sends
  - `main.py` — Low-level Gmail API wrapper
- **Setup**: Requires `credentials.json` (Google OAuth) - generates `token.json` on first run

#### `fast_api/` — REST API Service
- **Purpose**: Expose processed news and recommendations via HTTP endpoints
- **Key Files**:
  - `main.py` — FastAPI application with CORS middleware
- **Endpoints**:
  - `GET /` — API information
  - `GET /api/merged-news` — Retrieve categorized news from `merged_news.json`

### Typical Workflows

#### 1. Orchestrator Pipeline (CLI)

**First end-to-end run (fetch → score → RAG → email):**
```bash
export OPENAI_API_KEY=your_openai_key
python -m orchestrator.main
```

- If `orchestrator/prety_news.json` is empty or missing:
  - Fetches news (Perigon API or Yahoo RSS) for symbols in `news_agent/`
  - Scores each item with relevance (0 to 1) and sentiment (-1 to 1)
  - Saves scored news to `orchestrator/prety_news.json`
  - Builds RAG prompt and calls RAG backend over client PDF
  - Appends RAG summary to `orchestrator/output.txt`
  - Generates consolidated emails per manager and sends via Gmail API
  - Logs email dispatch to `orchestrator/email_output.txt`

**Re-run with cached news (no refetch, no rescore):**
```bash
python -m orchestrator.main
```
- Auto-loads latest scored news from `orchestrator/prety_news.json` and skips fetch/score phase.

**Force re-score:** Delete `orchestrator/prety_news.json` and rerun.

#### 2. Client-Based Recommendations Flow

**Step 1: Categorize News**
```bash
python client_based_recommendation/catagorizeNews.py
```
- Reads `client_based_recommendation/prety_news.json` (or `orchestrator/prety_news.json`)
- Filters news with `relevance_score = 0`
- Groups by ticker and categorizes by topic
- Outputs to `client_based_recommendation/merged_news.json`

**Step 2: Generate Client Recommendations**
```bash
python client_based_recommendation/client_level_rec.py
```
- Reads `merged_news.json`
- Generates client-specific recommendations using RAG system
- Processes in batches to avoid timeouts
- Outputs to `prety_recommendation.txt`

#### 3. REST API Service

**Start FastAPI server:**
```bash
cd fast_api
uvicorn main:app --reload --port 8000
```

**Available endpoints:**
- `GET /` — API information
- `GET /api/merged-news` — Retrieve categorized news (from `merged_news.json`)
- `GET /docs` — Interactive API documentation (Swagger UI)
- `GET /redoc` — Alternative API documentation (ReDoc)

**Test endpoint:**
```bash
curl http://localhost:8000/api/merged-news
```

#### 4. Gmail Setup (First Time Only)

1. Create Google Cloud OAuth client (Desktop App) and download `credentials.json`
2. Place `credentials.json` in `email_sending_agent/`
3. On first run, browser opens for OAuth consent → creates `token.json`
4. Sender must match authorized account in `email_sending_agent/main.py`

**Security:** Never commit `credentials.json` or `token.json`.

---

### Data Storage and Outputs

#### Critical Persistent Storage (Must be preserved)
- **`cognium_codebase/rag_storage/`** (~51MB)
  - Knowledge graph, vector embeddings, caches
  - **Required for RAG system to function**
  - Should be volume-mounted in Docker deployments

#### Input Data
- **`cognium_codebase/data/`** — Input PDFs (client portfolios, financial reports)
- **`client_based_recommendation/prety_news.json`** — Scored news input for categorization

#### Output Files
- **`orchestrator/prety_news.json`** — Scored news cache (JSON format)
- **`orchestrator/output.txt`** — RAG summaries log
- **`orchestrator/email_output.txt`** — Email dispatch logs
- **`client_based_recommendation/merged_news.json`** — Categorized news (used by API)
- **`prety_recommendation.txt`** — Client recommendations output

#### Ephemeral Storage (Can be regenerated)
- **`cognium_codebase/output/`** (~181MB)
  - Parsed document outputs (JSON, MD, images)
  - Not required for runtime (RAG uses `rag_storage/`)
  - Can be excluded from Docker volumes

---

### Troubleshooting

- Ensure your venv is active and packages install into it. If needed:
  ```bash
  ./venv/bin/python -m pip install -r cognium_codebase/requirements.txt
  ./venv/bin/python -m streamlit run cognium_codebase/streamlit_app.py
  ```
- If you see numpy/pandas binary mismatches:
  ```bash
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install --upgrade --force-reinstall numpy pandas
  ```
- If parsing fails on a PDF, set a different parser via env:
  ```bash
  export RAG_PARSER=mineru   # default auto-detects docling else falls back to mineru
  ```
- Ensure `cognium_codebase/data`, `cognium_codebase/rag_storage`, and `cognium_codebase/output` are writable.
- If you see only raw news printed and no scores, verify `OPENAI_API_KEY` and `langchain-openai` are installed.
- Yahoo RSS is public but can rate-limit; re-run later or reduce symbol count if needed.
- Gmail sending:
  - Ensure `email_sending_agent/credentials.json` exists; delete `token.json` to re-consent if needed
  - Subjects are auto-branded with `[Cognium]` and bodies are formatted with client bullets
  - The agent consolidates to one email per manager; if you see duplicates, clear logs and re-run

### Configuration

#### News Sources
- **Change tickers/symbols**: Edit symbol list in `news_agent/main.py` or `news_agent/MultipleNewsSources.py`
- **Change news limit**: Modify `limit` parameter in news fetching functions
- **Switch news source**: Use `MultipleNewsSources.py` for Perigon API (requires `PERIGON_API_KEY`)

#### RAG System
- **Change client PDF path**: 
  - Orchestrator: Update `file_path` in `orchestrator/main.py` (line ~245)
  - Client recommendations: Update `file_path` in `client_based_recommendation/client_level_rec.py` (line ~140)
- **Parser selection**: Set `RAG_PARSER=docling` or `RAG_PARSER=mineru` in `.env` (default: auto-detect)

#### API Configuration
- **Change port**: Modify `--port` in uvicorn command
- **CORS origins**: Update `allow_origins` in `fast_api/main.py` for production

### Docker Deployment (Future)

The project is structured for Docker deployment with:
- Root-level `requirements.txt` for all dependencies
- Separate services that can be containerized independently
- Persistent storage requirements identified (`rag_storage/`)

**Recommended architecture:**
- **API Container**: FastAPI service (lightweight, port 8000)
- **Processor Container**: Orchestrator + news agent + client recommendations
- **Shared Volumes**: `rag_storage/`, `client_based_recommendation/`, `orchestrator/`

---

### License

No license file is included. If you plan to share or publish, add a license of your choice.


