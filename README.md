## Cognium RAG Agents (CLI-only: News → Scoring → RAG → Email)

End-to-end command-line workflow:

- Fetch recent news per ticker/index (Yahoo Finance RSS, no API key)
- Score each news item (relevance and sentiment) with OpenAI via LangChain
- Run a RAG pipeline against a client-portfolio PDF to produce per-client notes grouped by ticker
- Email managers consolidated updates (one per manager) via Gmail API

### Repo layout

- `cognium_codebase/` — RAGAnything demo (Streamlit UI + async backend)
  - `streamlit_app.py` — upload → ingest → query
  - `main.py` — async function to ingest/query programmatically
  - `requirements.txt` — core deps for the RAG UI and backend
  - `data/` — sample PDFs
  - `rag_storage/` — local knowledge store (chunks/entities/relations/cache)
  - `output/` — per-document parsed outputs
- `news_agent/` — LangChain agent with web search (Tavily)
- `orchestrator/` — runs the news agent, then queries the RAG and logs output

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

# Core RAG deps
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r cognium_codebase/requirements.txt

# Scoring + email deps
python -m pip install "langchain-openai>=0.1"
python -m pip install google-auth google-auth-oauthlib google-api-python-client
```

Create a `.env` file at the repo root (and/or export in your shell):

```bash
OPENAI_API_KEY=your_openai_key
```

These env vars are read by the components via `python-dotenv`.

---

### Component overview

- `cognium_codebase/` — RAGAnything demo (async backend)
  - `main.py` — async ingest/query function used by the orchestrator
  - `requirements.txt` — dependencies for parsing and RAG
  - `data/` — sample PDFs (e.g., `private_bank_clients_100.pdf`)
  - `rag_storage/` — working store (chunks/entities/relations/cache)
  - `output/` — per-document parsed outputs
- `news_agent/` — Yahoo Finance RSS fetcher
  - `main.py` — returns a dict: `{symbol: [ {date, publisher, title, link, summary}, ... ] }`
  - Symbols list is inside `main.py`
- `orchestrator/` — CLI pipeline
  - `main.py` — loads previously scored news if present, else fetches+scores; then calls RAG and logs; finally sends consolidated manager emails
  - `prety_news.txt` — append-only log; contains `scored_news` JSON blocks
  - `output.txt` — append-only log; contains RAG summaries
  - `email_output.txt` — append-only log; contains email dispatch logs
- `email_sending_agent/` — Gmail sender and agent wrapper
  - `main.py` — low-level Gmail send (`gmail_send_message(to, subject, body)`)
  - `agent.py` — creates ONE polished, consolidated email per manager from RAG text and sends it
  - `credentials.json` — place your Google OAuth client file here (not in repo)
  - `token.json` — created on first OAuth run

### Typical workflows (CLI)

1) First end-to-end run (fetch → score → RAG)
```bash
export OPENAI_API_KEY=your_openai_key
python -m orchestrator.main | cat
```
- If `orchestrator/prety_news.txt` has no `scored_news` yet, the pipeline:
  - fetches news (Yahoo RSS) for the symbols in `news_agent/main.py`
  - scores each item with relevance (0..1) and sentiment (−1..1)
  - appends a `scored_news` JSON block to `orchestrator/prety_news.txt`
  - builds a precise prompt and calls the RAG backend over your PDF
  - appends the RAG summary to `orchestrator/output.txt`
  - generates ONE consolidated email per manager and sends via Gmail API
  - appends email logs to `orchestrator/email_output.txt` and `orchestrator/output.txt`

2) Re-run only the RAG step with cached news (no refetch, no rescore)
```bash
python -m orchestrator.main | cat
```
- The orchestrator will auto-load the latest `scored_news` block from `orchestrator/prety_news.txt` and skip the news fetch/score phase.

3) Refresh news symbols or volume
- Edit the symbols list in `news_agent/main.py`
- Optionally change the `limit` passed to `get_news_for_symbols`
- Re-run step (1)

4) Configure Gmail sending (first time only)
- Create a Google Cloud OAuth client (Desktop App) and download `credentials.json`
- Place `credentials.json` in `email_sending_agent/`
- On first end-to-end run, a browser will open to consent; this creates `email_sending_agent/token.json`
- The sender must match the authorized account inside `email_sending_agent/main.py` (`message["From"]`)

---

### Outputs

- `orchestrator/prety_news.txt` — contains timestamped `scored_news` JSON blocks
- `orchestrator/output.txt` — contains timestamped RAG summaries
- `orchestrator/email_output.txt` — contains timestamped email dispatch logs

### Data, storage, and outputs

- Input PDFs: `cognium_codebase/data/`
- Working store: `cognium_codebase/rag_storage/` (chunks, entities, relationships, caches)
- Per-document outputs: `cognium_codebase/output/<doc-name>/...`
- Orchestrated run log: `orchestrator/output.txt`

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

---

### License

No license file is included. If you plan to share or publish, add a license of your choice.


