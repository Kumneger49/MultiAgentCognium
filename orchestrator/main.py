import json
from datetime import datetime
import asyncio
from typing import List, Dict, Any

# from news_agent.main import main as newsmain
from news_agent.MultipleNewsSources import main as newsmain
from cognium_codebase.main import main as ragmain

# Email agent import (optional - may fail due to langchain version compatibility)
try:
    from email_sending_agent.agent import run_email_agent
except ImportError as e:
    print(f"Warning: Could not import email_sending_agent: {e}")
    print("Email functionality will be disabled. Fix langchain compatibility to enable.")
    run_email_agent = None

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None  # will error later if not installed



def _flatten_news(batch: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    print("-------------------------------------------Flattening the news-------------------------------------------")
    items: List[Dict[str, Any]] = []
    for ticker, entries in (batch or {}).items():
        for e in entries or []:
            items.append({
                "ticker": ticker,
                "date": e.get("published", "")[:10],  # YYYY-MM-DD
                "title": e.get("title", ""),
                "summary": e.get("summary", ""),
                "link": e.get("url", ""),           # Copy 'url' from input
                "source": e.get("source", ""),      # Copy 'source' from input
            })
    return items



def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    print("-------------------------------------------Extracting json-------------------------------------------")
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        return json.loads(text)
    except Exception:
        return []


def _load_scored_news_from_file(path: str) -> List[Dict[str, Any]]:
    print("-------------------------------------------Loading the scored news-------------------------------------------")
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return []
    # Find last marker line for scored_news
    last_idx = -1
    for i, line in enumerate(lines):
        if "scored_news" in line:
            last_idx = i
    if last_idx == -1:
        # Fallback: try to parse last JSON array in file
        text = "\n".join(lines)
        return _extract_json_array(text)
    # Collect subsequent lines until a blank separator
    payload_lines: List[str] = []
    for j in range(last_idx + 1, len(lines)):
        if not lines[j].strip():
            break
        payload_lines.append(lines[j])
    payload = "\n".join(payload_lines).strip()
    return _extract_json_array(payload)


def score_news_with_llm(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not ChatOpenAI:
        raise RuntimeError("langchain_openai is not installed. pip install langchain-openai")
    if not items:
        return []

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    schema_hint = {
        "ticker": "string",
        "date": "YYYY-MM-DD",
        "title": "string",
        "summary": "string",
        "link": "string (must be copied exactly from the input 'url' field)",
        "relevance_score": "0 to 1 (how directly related to the ticker/company)",
        "sentiment_score": "-1 to 1 (negative to positive expected impact)",
        "reason": "one sentence",
        "tag": "a word for category",
        "source": "must be copied exactly from the input 'source' field, do NOT hallucinate"
    }

    prompt = (
        "You are a financial assistant. For EACH news item in the input list, do the following:\n"
        "1. Copy the 'title' and 'summary' exactly.\n"
        "2. Copy 'url' from input as 'link'.\n"
        "3. Copy 'source' from input as 'source'. Do NOT make up sources.\n"
        "4. Extract the date from the 'published' field and format as YYYY-MM-DD.\n"
        "5. Add 'ticker' and assign the correct ticker.\n"
        "6. Assign 'tag' as one word: Tech, Stocks, Bonds, or Other.\n"
        "7. Assign 'relevance_score' (0 to 1) based on how directly the news affects the ticker.\n"
        "8. Assign 'sentiment_score' (-1 to 1) for expected impact on the ticker.\n"
        "9. Add a one-sentence 'reason' explaining your scores.\n\n"
        "Return ONLY a JSON array (no prose) matching the schema below exactly. "
        "Do not leave 'source' or 'link' empty and do not invent them.\n"
        f"{json.dumps(schema_hint)}\n"
    )



    messages = [
        ("system", "You return only JSON arrays, no extra text."),
        ("user", prompt),
        ("user", json.dumps(items, ensure_ascii=False)),
    ]

    result = llm.invoke([{"role": r, "content": c} for r, c in messages])
    content = getattr(result, "content", "") or ""
    scored = _extract_json_array(content)
    return scored


def main() -> List[Dict[str, Any]]:
    # Load previously scored news to avoid re-fetching every run
    scored = _load_scored_news_from_file("./orchestrator/prety_news.json")
    if not scored:
        # Fallback: fetch and score now
        print("News has not been scored yet, scoring now")
        batch = newsmain()
        items = _flatten_news(batch)
        scored = score_news_with_llm(items)

        # Pretty print
        if scored:
            print("\nScored news (showing up to 10):")
            for i, it in enumerate(scored[:10], 1):
                print(f"{i:02d}. {it.get('ticker','')} | Rel={it.get('relevance_score')} | Sent={it.get('sentiment_score')} | {it.get('title','')}")
        else:
            print("\nRanking step returned no items (check OPENAI_API_KEY and langchain-openai installation).")

        # Append to orchestrator log
        output_file = "./orchestrator/prety_news.json"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(output_file, "a", encoding="utf-8") as f:
            # json.dump(f"[{now}] scored_news\n", f)
            json.dump(scored, f)

    # ============================== RAG INTEGRATION ==============================
    # Build a precise prompt: map scored news → affected tickers → impacted clients with concise actions
    print("Detected news has been scored, building RAG prompt")
    rag_prompt_template = f"""
        You are a financial research assistant with expertise in analyzing market news and client portfolios. 
        Your role is to interpret financial data, write personalized notes for clients, and then prepare manager-level email drafts. 

        ### Inputs:
        News items (JSON):
        Ticker: __________
        Date: __________
        Title: __________
        Summary: __________
        Relevance Score: __________
        Sentiment Score: __________

        Client profiles (JSON):
        Client ID: __________
        First Name: __________
        Last Name: __________
        Risk Capacity: __________
        Risk Tolerance: __________
        Primary Goals: __________
        Interview Log: __________
        Holdings: __________

        News items: {json.dumps(scored, ensure_ascii=False)}

        ### Step 1. Filter news
        - Skip news if relevance score < 0.2.
        - Interpret sentiment score (-1 to 1):
            * > 0.3 → Favorable
            * -0.3 to 0.3 → Neutral
            * < -0.3 → Adverse

        ### Step 2. Ticker-level summary
        - Write a 2–3 sentence plain-text summary combining title, summary, and sentiment.

        ### Step 3. Client-level notes
        For **every client holding the affected ticker** (not optional, all must be included):
            - Date: __________
            - Impact: 2–3 sentences on how this news may affect the client’s holdings (upside + downside).
            - Profile: reference risk capacity, tolerance, and goals; include a short snippet from interview log if useful.
            - Suggested Action (rules):
                * Sentiment > 0.3 → BUY or HOLD, justify.
                * -0.3 to 0.3 → HOLD or WATCH CLOSELY, justify.
                * Sentiment < -0.3 → SELL or REDUCE, unless high tolerance + long-term goals → CAUTIOUS HOLD.

        Keep each client note under 6 lines. **Do not skip any client that holds the ticker.**

        ### Step 4. Manager grouping
        Clients are assigned to managers as follows:
            - Manager 1(email: kumnegermarkos49@gmail.com): IDs 1–20
            - Manager 2(email: ken496235@gmail.com): IDs 21–40
            - Manager 3(email: kumneger496235@gmail.com): IDs 41–60
            - Manager 4(email: kumnegermarkos49@gmail.com): IDs 61–80
            - Manager 5(email: kumneger496235@gmail.com): IDs 81–100
            (If more clients exist, continue assigning in blocks of 20.)

        Group affected clients by their manager.

        ### Step 5. Manager email drafts
        For each manager with affected clients:

        1. **Mandatory client coverage:**
            - The model must identify **all tickers mentioned in the news** (no skipping).
            - For each ticker, search all clients’ holdings and find **every client holding that ticker**.
            - For each client found, generate a dedicated mini-email update. **No affected client may be omitted.**

        2. **Per-client mini-email format:**
            Each client’s update must be a **standalone mini-email** with:
                - **Client Name and ID**
                - **Subject line** – reflects the news/update affecting this client.
                - **Intro** – brief context of the news or market event.
                - **Body** – explain what happened, why it matters, and impact on this client’s holdings. Explicitly reference their risk capacity, tolerance, goals, and interview log snippet if useful.
                - **Closing** – suggest a clear action or next step (aligned with Step 3 rules).

        3. **Manager draft structure:**
            - Start with a short intro paragraph explaining that detailed updates are being provided for each affected client.
            - Then include **each client’s mini-email individually** in sequence. Do **not merge multiple clients** into one bullet or paragraph.
            - Ensure the draft is **fully exhaustive**: every client affected by any news item must be included.

        4. **Style rules:**
            - Keep each mini-email concise, professional, and actionable.
            - Each mini-email must be readable independently.
            - End the manager draft with a polite closing line offering to discuss further.

        **CRITICAL RULE:** The model must **systematically identify all affected tickers and all affected clients for each news item**. Completeness is required before generating the manager email drafts.
        """




    print("----------------------------calling the rag agent-------------------------------")
    # Use absolute path to ensure cache consistency (RAGAnything uses full path in cache key)
    import os
    file_path = os.path.abspath("./cognium_codebase/data/private_bank_clients_100.pdf")
    rag_final_answer = asyncio.run(
        ragmain(
            rag_prompt_template,
            file_path=file_path,
        )
    )

    # Append RAG answer to log
    output_file = "./orchestrator/output.txt"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"[{now}] rag_summary\n")
        f.write(rag_final_answer + "\n\n")

    print("RAG agent has finished, returning the final answer")
    print(rag_final_answer)

    # ============================== EMAIL SENDING AGENT ==============================
    # Pass the RAG output to the email agent. The agent extracts manager emails and sends messages.
    email_logs = []
    if run_email_agent is None:
        print("Skipping email dispatch: email_sending_agent not available (langchain compatibility issue)")
    else:
        print("Dispatching emails to managers via email_sending_agent...")
        try:
            email_logs = run_email_agent(rag_final_answer)
        except Exception as exc:
            print(f"Email agent failed: {exc}")

    if email_logs:
        print("\nEmail dispatch logs:")
        for e in email_logs:
            print(f"to={e.get('to','')} | subject={e.get('subject','')} | status={e.get('status','')}")

    email_output_file = "./orchestrator/email_output.txt"
    with open(email_output_file, "a", encoding="utf-8") as f:
        f.write(f"[{now}] email_logs\n")
        f.write(json.dumps(email_logs, ensure_ascii=False) + "\n\n")

    # Append email logs to orchestrator log
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"[{now}] email_logs\n")
        f.write(json.dumps(email_logs, ensure_ascii=False) + "\n\n")

    return scored


if __name__ == "__main__":
    main()


# print(asyncio.run(ragmain(question, file_path="data/private_bank_clients_100.pdf")))



# rag_summary = "../cognium_codebase/client_summary.txt"
# news_data = f"{main()}"

# orchestrator_prompt = f"""
# You are a financial orchestrator agent. You are given:

# 1. An aggregated summary of client holdings, portfolio patterns, and key investment properties:
# {rag_summary}

# 2. A structured set of recent news and events affecting these holdings:
# {news_data}

# Your task is to produce a **final, user-friendly summary** that explains:

# - How recent news or events could **impact each holding or asset**.  
# - Key trends, risks, and opportunities for the portfolio.  
# - Practical, actionable insights for a user who owns or is considering these holdings.  

# Follow these guidelines:

# 1. Present the summary in **clear, human-readable paragraphs**, not JSON.  
# 2. For each major holding or asset type, include:
#    - The ticker or company name.
#    - What the news means for its performance or value.
#    - Any implications for clients with similar portfolio patterns (e.g., growth-focused, balanced, risk-averse).  
# 3. Highlight **general portfolio patterns** affected by news, such as sectors or regions experiencing trends.  
# 4. Be concise, informative, and suitable for a user wanting to understand **how their investments may be affected**.

# Example style:

# "NVDA (NVIDIA) has recently reported strong earnings and increasing demand for AI chips, indicating potential growth for technology-focused portfolios. Growth-oriented investors may benefit from increased exposure, while risk-averse clients should monitor market volatility.

# US Government Bonds (US10Y) are seeing rising yields, which may slightly reduce bond prices. Clients with high fixed-income allocations should consider the impact on their portfolios.

# Overall, the client base shows significant exposure to US and APAC equities, with balanced portfolios benefiting from diversification across sectors. Recent news suggests strong opportunities in technology and emerging markets, but rising interest rates could affect fixed-income returns."
# """

# print(asyncio.run(ragmain(question, file_path="data/private_bank_clients_100.pdf")))



# rag_summary = "../cognium_codebase/client_summary.txt"
# news_data = f"{main()}"

# orchestrator_prompt = f"""
# You are a financial orchestrator agent. You are given:

# 1. An aggregated summary of client holdings, portfolio patterns, and key investment properties:
# {rag_summary}

# 2. A structured set of recent news and events affecting these holdings:
# {news_data}

# Your task is to produce a **final, user-friendly summary** that explains:

# - How recent news or events could **impact each holding or asset**.  
# - Key trends, risks, and opportunities for the portfolio.  
# - Practical, actionable insights for a user who owns or is considering these holdings.  

# Follow these guidelines:

# 1. Present the summary in **clear, human-readable paragraphs**, not JSON.  
# 2. For each major holding or asset type, include:
#    - The ticker or company name.
#    - What the news means for its performance or value.
#    - Any implications for clients with similar portfolio patterns (e.g., growth-focused, balanced, risk-averse).  
# 3. Highlight **general portfolio patterns** affected by news, such as sectors or regions experiencing trends.  
# 4. Be concise, informative, and suitable for a user wanting to understand **how their investments may be affected**.

# Example style:

# "NVDA (NVIDIA) has recently reported strong earnings and increasing demand for AI chips, indicating potential growth for technology-focused portfolios. Growth-oriented investors may benefit from increased exposure, while risk-averse clients should monitor market volatility.

# US Government Bonds (US10Y) are seeing rising yields, which may slightly reduce bond prices. Clients with high fixed-income allocations should consider the impact on their portfolios.

# Overall, the client base shows significant exposure to US and APAC equities, with balanced portfolios benefiting from diversification across sectors. Recent news suggests strong opportunities in technology and emerging markets, but rising interest rates could affect fixed-income returns."
# """

