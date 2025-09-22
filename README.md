## Cognium RAG Agents (RAG UI + News Agent + Orchestrator)

Simple end-to-end demo showing:

- RAG UI to upload PDFs and ask questions (Streamlit)
- A news agent that fetches recent news for tickers/companies (LangChain + Tavily)
- An orchestrator that combines the two: pulls news, asks the RAG over your client data, and writes a final summary

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
- A Tavily API key (`TAVILY_API_KEY`) for web search in `news_agent`

---

### Setup (once)

```bash
python3 -m venv venv
source venv/bin/activate
python -V   # should be 3.11.9 or newer

# Core RAG deps
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r cognium_codebase/requirements.txt

# News agent + LangChain deps
python -m pip install "langchain>=0.2" "langchain-openai>=0.1" "langchain-community>=0.2" tavily-python python-dotenv
```

Create a `.env` file at the repo root (and/or export in your shell):

```bash
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
```

These env vars are read by the components via `python-dotenv`.

---

### Option A: Run the Streamlit RAG UI

```bash
cd cognium_codebase
python -m streamlit run streamlit_app.py
```

Then open the URL shown in terminal. In the sidebar you can:

- Upload a PDF (or use the sample files in `cognium_codebase/data/`)
- Ingest and build the local knowledge store
- Ask questions; answers are generated with hybrid retrieval

Notes:

- Defaults: text model `gpt-4o-mini`, VLM `gpt-4o-mini`, embeddings `text-embedding-3-large`
- Stores output under `cognium_codebase/output/` and working data under `cognium_codebase/rag_storage/`

---

### Option B: Call the RAG backend programmatically

Example (from repo root):

```bash
python - <<'PY'
import asyncio
from cognium_codebase.main import main as rag_main

query = "Summarize the document"
file_path = "cognium_codebase/data/private_bank_clients_100.pdf"

print(asyncio.run(rag_main(query=query, file_path=file_path)))
PY
```

---

### Run the News Agent

The news agent reads `cognium_codebase/client_summary.txt`, identifies relevant tickers/companies, and fetches recent news using Tavily.

```bash
cd news_agent
python main.py | cat
```

Output is a structured JSON-like string printed to stdout.

---

### Run the Orchestrator (News → RAG → Final Summary)

Open `orchestrator/main.py` and update the hard-coded PDF path to a path that exists on your machine. Change this line to a relative path pointing to the bundled sample file:

```python
rag_final_answer = asyncio.run(
    ragmain(rag_prompt_template,
            file_path = "./cognium_codebase/data/private_bank_clients_100.pdf")
)
```

Then run:

```bash
cd orchestrator
python main.py | cat
```

This will:

- Run the news agent to get recent events
- Ask the RAG over your client PDF data to produce an investor-friendly summary
- Append the final summary to `orchestrator/output.txt` and print it to the console

---

### Orchestrator Frontend (Streamlit)

Run a minimal UI at the repo root to fetch news and generate the RAG summary in one click:

```bash
python -m streamlit run orchestrator_app.py
```

In the sidebar you can set the PDF path (defaults to `./cognium_codebase/data/private_bank_clients_100.pdf`) and whether to append results to `orchestrator/output.txt`. Click "Get News + Generate Summary" to see step-by-step progress, the raw news payload, and the final summary.

---

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
- If parsing fails for a PDF in the UI, try a different parse method in the sidebar (e.g., `ocr` or `auto`) and ensure `cognium_codebase/data`, `cognium_codebase/rag_storage`, and `cognium_codebase/output` are writable.
- News agent requires `TAVILY_API_KEY`. If missing, search will fail.
- Orchestrator uses a file path for the RAG input PDF; update it as shown above.

---

### License

No license file is included. If you plan to share or publish, add a license of your choice.


