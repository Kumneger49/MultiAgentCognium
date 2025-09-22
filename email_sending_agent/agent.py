from typing import List, Dict, Any
import re
import json

from pydantic import BaseModel, Field
from langchain.agents import initialize_agent, tool
from langchain_openai import ChatOpenAI

from email_sending_agent.main import gmail_send_message


class SendEmailInput(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text")


@tool("send_email", args_schema=SendEmailInput)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail API to a recipient with a subject and body."""
    try:
        gmail_send_message(to, subject, body)
        return f"sent:{to}"
    except Exception as exc:
        return f"error:{to}:{exc}"


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        return json.loads(text)
    except Exception:
        return []


def run_email_agent(rag_text: str) -> List[Dict[str, Any]]:
    """
    Plan consolidated, one-per-manager emails from the RAG text, then send once per manager.
    Returns list of logs: {to, subject, status}.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    planner_instructions = (
        "You are given a plain-text report with per-ticker client notes and manager groupings.\n"
        "Extract all manager email addresses (pattern: user@domain). For each distinct manager,\n"
        "create ONE consolidated email that includes all impacted clients they manage.\n"
        "Formatting requirements:\n"
        "- subject MUST begin with '[Cognium] ' followed by a concise summary (e.g., '[Cognium] Portfolio Updates for <Manager>' or include key tickers).\n"
        "- body MUST be polished and easy to skim, using this structure in plain text:\n"
        "  Dear <Manager Name or 'Manager'>,\n\n"
        "  Here are the latest portfolio updates based on recent market developments:\n\n"
        "  ---\n"
        "  For each affected client (one block per client):\n"
        "  - Client: <First Last> (ID: <id>)\n"
        "    • Ticker: <TICKER>\n"
        "    • Impact: <1–2 sentences tied to sentiment/summary>\n"
        "    • Suggested Action: <one sentence, e.g., Monitor / Trim / Add / Hedge / Diversify>\n"
        "    • Rationale: <one short sentence referencing risk capacity/tolerance/goals>\n"
        "  ---\n\n"
        "  If you would like, I can prepare trade-ready recommendations or deeper analysis.\n\n"
        "  Best regards,\n"
        "  Cognium Research Assistant\n"
        "Return ONLY a JSON array: [{to, subject, body}] with exactly one item per manager. No extra text.\n"
        "Do not repeat the same manager more than once."
    )

    plan_messages = [
        {"role": "system", "content": planner_instructions},
        {"role": "user", "content": rag_text},
    ]
    plan_result = llm.invoke(plan_messages)
    plan_text = getattr(plan_result, "content", "") or ""
    planned = _extract_json_array(plan_text)

    logs: List[Dict[str, Any]] = []
    seen: set = set()
    for item in planned:
        to = (item.get("to") or "").strip()
        subject = (item.get("subject") or "").strip()
        body = (item.get("body") or "").strip()
        if not to:
            continue
        key = (to.lower(), subject)
        if key in seen:
            continue
        seen.add(key)
        try:
            gmail_send_message(to, subject, body)
            logs.append({"to": to, "subject": subject, "status": "sent"})
        except Exception as exc:
            logs.append({"to": to, "subject": subject, "status": f"error:{exc}"})

    return logs


