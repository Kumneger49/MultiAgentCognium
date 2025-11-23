import json
import sys
import re
import asyncio
import traceback
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from news_agent.main import get_news_for_symbols
from cognium_codebase.main import main as ragmain, init_rag, query_rag

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency handled at runtime
    ChatOpenAI = None

# Resolve paths relative to repository root
PRETTY_NEWS_PATH = SCRIPT_DIR / "prety_news.json"
MERGED_NEWS_PATH = SCRIPT_DIR / "merged_news.json"
RECOMMENDATIONS_PATH = PROJECT_ROOT / "prety_recommendation.json"
PDF_PATH = SCRIPT_DIR / "output.pdf"

# Recommendation generation prompt template
RECOMMENDATION_PROMPT_TEMPLATE = """
MANDATORY TASK: Generate client recommendations for ALL {batch_count} news items in this batch. You MUST process every single one.

MINIMUM REQUIREMENTS:
- Batch items to process: {batch_count}
- High relevance (rel>=0.7): Generate 4-5 recommendations per item
- Medium relevance (0.5<=rel<0.7): Generate 3-4 recommendations per item  
- Standard relevance (0.2<=rel<0.5): Generate 2-3 recommendations per item
- MINIMUM total recommendations for this batch: {batch_min_recommendations}

Priority rules:
- Process items in order (highest relevance first)
- For rel>=0.7: Generate 4-5 client recommendations (HIGH PRIORITY)
- For 0.5<=rel<0.7: Generate 3-4 client recommendations (MEDIUM PRIORITY)
- For 0.2<=rel<0.5: Generate 2-3 client recommendations (STANDARD)
- Analyze client portfolios deeply - match holdings, sectors, risk profiles

Key factors (all required):
1. Rate of return (quantitative estimate with %)
2. Portfolio risk (numerical estimate with %)
3. Bank commissions (quantitative prediction with %)

Requirements:
- Generate recommendations for ALL {batch_count} news items - DO NOT STOP EARLY
- Use exact "src" array from data (don't modify)
- Format news as "Topic: [topic]\\nSummary: [sum]"
- Dig deep into portfolio analysis - consider indirect impacts, sector effects, market sentiment
- For high-relevance news, analyze multiple angles: direct holdings, sector exposure, supply chain, competitive landscape

OUTPUT FORMAT: You MUST return ONLY a valid JSON array. No markdown, no explanations, no text before or after. Just the JSON array.

Example format:
[
  {{
    "ticker": "AAPL",
    "news": "Topic: Apple's Market Valuation\\nSummary: Apple has surpassed $4 trillion",
    "sources": [{{"name": "cnn.com", "title": "...", "link": "..."}}],
    "client_name": "John Doe",
    "recommendation": "2 sentences connecting all 3 factors",
    "rate_of_return": "3-5% increase",
    "portfolio_risk": "8% decline",
    "bank_commissions": "2-3% growth",
    "tag": "Tech, Stocks"
  }}
]

Required keys for each recommendation:
- "ticker": use the ticker from the data
- "news": "Topic: [topic]\\nSummary: [sum]" (from data)
- "sources": use exact "src" array from data (must be an array)
- "client_name": client name from portfolio
- "recommendation": "2 sentences connecting all 3 factors"
- "rate_of_return": "estimate with % (e.g., 3-5% increase)"
- "portfolio_risk": "estimate with % (e.g., 8% decline)"
- "bank_commissions": "estimate with % (e.g., 2-3% growth)"
- "tag": "Tech, Stocks, Bonds, Finance or other"

CRITICAL: 
1. Return ONLY valid JSON array - no other text
2. Process ALL {batch_count} news items - do not stop early
3. Each recommendation must be a complete JSON object with all required keys

News items (batch {batch_num}/{total_batches}, sorted by relevance - process ALL {batch_count}):
{new}
"""

DEFAULT_TICKERS = [
    "INFY.NS",
    "TM",
    "SPY",
    "AAPL",
    "TSLA",
    "BND",
    "AGG",
    "GLD",
    "EEM",
    "IAU",
    "SIE.DE",
    "IGLS.L",
    "MSFT",
]


def _flatten_news(batch: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalize per-ticker article batches into a flat list for scoring."""
    print("Flattening Yahoo Finance news payload...")
    items: List[Dict[str, Any]] = []
    for ticker, entries in (batch or {}).items():
        for entry in entries or []:
            published = entry.get("date") or entry.get("published") or ""
            try:
                published = published[:10] if published else ""
            except Exception:
                published = str(published)

            items.append(
                {
                    "ticker": ticker,
                    "date": published,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", entry.get("url", "")),
                    "source": entry.get("publisher", entry.get("source", "")),
                }
            )
    return items


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        return json.loads(text)
    except Exception:
        return []


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
        "link": "string (copy the original link exactly)",
        "relevance_score": "0 to 1",
        "sentiment_score": "-1 to 1",
        "reason": "one sentence",
        "tag": "Tech|Stocks|Bonds|Other",
        "source": "copy the original source exactly",
    }

    prompt = (
        "You are a financial assistant. For EACH news item in the input list:\n"
        "1. Copy title and summary exactly.\n"
        "2. Copy link/source exactly (do not invent them).\n"
        "3. Use the provided ticker and date.\n"
        "4. Provide a relevance_score (0-1) and sentiment_score (-1 to 1).\n"
        "5. Provide a one-sentence reason and a one-word tag.\n"
        "Return ONLY a JSON array matching this schema:\n"
        f"{json.dumps(schema_hint)}"
    )

    messages = [
        ("system", "You return only JSON arrays, no extra text."),
        ("user", prompt),
        ("user", json.dumps(items, ensure_ascii=False)),
    ]

    result = llm.invoke([{"role": role, "content": content} for role, content in messages])
    content = getattr(result, "content", "") or ""
    scored = _extract_json_array(content)
    return scored


def _extract_json_from_response(text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _categorize_ticker_news(
    ticker: str, articles: List[Dict[str, Any]], llm: Any
) -> Dict[str, Any]:
    """Categorize and merge news articles for a single ticker using LLM."""
    # Limit articles to avoid token limits
    articles_to_process = articles[:20] if len(articles) > 20 else articles
    formatted_articles = json.dumps(articles_to_process, indent=2)

    prompt_text = f"""You are a factual, neutral, and precise news summarizer and categorizer.

ABSOLUTE REQUIREMENT: You MUST use ONLY the articles provided below. Do NOT invent, hallucinate, or create any data that is not in the provided articles.

You will receive a JSON array of news articles for ticker {ticker}. Each article has:
- "title": the actual article title
- "summary": the actual article summary  
- "link": the actual article URL
- "source": the actual source domain
- "date": the publication date
- "relevance_score": relevance score (0.0 to 1.0) - already filtered to only include relevant articles
- "sentiment_score": sentiment score (-1.0 to 1.0) indicating positive/negative sentiment

Your tasks:
1. Read each article's title, summary, link, source, relevance_score, and sentiment_score from the JSON below
2. Group articles that cover the same topic or event together
3. For each group, create an object with:
   - "topic": a short descriptive title based on the ACTUAL article titles/summaries
   - "summary": a 2-3 sentence summary based ONLY on the actual article summaries provided
   - "relevance_score": calculate the average (mean) of all relevance_score values from articles in this group
   - "sentiment_score": calculate the average (mean) of all sentiment_score values from articles in this group
   - "sources": a list where each object contains EXACTLY:
       - "name": copy the "source" field from the article
       - "title": copy the "title" field from the article
       - "link": copy the "link" field from the article
       - "relevance_score": copy the exact "relevance_score" value from the article
       - "sentiment_score": copy the exact "sentiment_score" value from the article
4. If an article is unique, it becomes its own category

CRITICAL: Every "name", "title", "link", "relevance_score", and "sentiment_score" in your response MUST match exactly what is in the articles array below. Do NOT create fictional data.

Return ONLY valid JSON with this exact structure:
{{
  "ticker": "{ticker}",
  "categories": [
    {{
      "topic": "topic name based on actual articles",
      "summary": "summary based on actual article summaries",
      "relevance_score": average_relevance_score,
      "sentiment_score": average_sentiment_score,
      "sources": [
        {{
          "name": "exact source from article",
          "title": "exact title from article",
          "link": "exact link from article",
          "relevance_score": exact_relevance_score_from_article,
          "sentiment_score": exact_sentiment_score_from_article
        }}
      ]
    }}
  ]
}}

Ticker: {ticker}
Articles (copy the exact values from these):
{formatted_articles}
"""

    try:
        response = llm.invoke(prompt_text)
        response_text = response.content if hasattr(response, "content") else str(response)
        cleaned_response = _extract_json_from_response(response_text)
        merged_json = json.loads(cleaned_response)

        # Ensure ticker matches
        if merged_json.get("ticker") != ticker:
            merged_json["ticker"] = ticker

        # Post-process: ensure scores are included in sources
        article_lookup = {}
        for art in articles_to_process:
            title = art.get("title", "").strip().lower()
            link = art.get("link", "").strip().lower()
            article_lookup[title] = art
            article_lookup[link] = art

        for cat in merged_json.get("categories", []):
            relevance_scores = []
            sentiment_scores = []

            for source in cat.get("sources", []):
                title = source.get("title", "").strip().lower()
                link = source.get("link", "").strip().lower()
                matching_article = article_lookup.get(title) or article_lookup.get(link)

                if matching_article:
                    if "relevance_score" not in source:
                        source["relevance_score"] = matching_article.get("relevance_score", 0)
                    if "sentiment_score" not in source:
                        source["sentiment_score"] = matching_article.get("sentiment_score", 0)

                    relevance_scores.append(source.get("relevance_score", 0))
                    sentiment_scores.append(source.get("sentiment_score", 0))

            # Calculate category-level averages
            if relevance_scores:
                if "relevance_score" not in cat or cat.get("relevance_score") is None:
                    cat["relevance_score"] = sum(relevance_scores) / len(relevance_scores)
                if "sentiment_score" not in cat or cat.get("sentiment_score") is None:
                    cat["sentiment_score"] = sum(sentiment_scores) / len(sentiment_scores)

        return merged_json
    except Exception as e:
        print(f"✗ Error categorizing {ticker}: {e}")
        # Return empty structure on error
        return {"ticker": ticker, "categories": []}


def categorize_and_merge_news(
    input_path: Path = PRETTY_NEWS_PATH,
    output_path: Path = MERGED_NEWS_PATH,
) -> List[Dict[str, Any]]:
    """Load scored news, categorize/merge by ticker, and write merged_news.json."""
    if not ChatOpenAI:
        raise RuntimeError("langchain_openai is not installed. pip install langchain-openai")

    print(f"Loading scored news from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        news_items = json.load(f)

    print(f"Loaded {len(news_items)} news items")

    # Filter out irrelevant news (relevance_score = 0)
    filtered_news_items = [n for n in news_items if n.get("relevance_score", 0) != 0]
    print(f"Filtered out {len(news_items) - len(filtered_news_items)} items with relevance_score = 0")
    print(f"Processing {len(filtered_news_items)} relevant news items")

    # Group news by ticker
    grouped = defaultdict(list)
    for n in filtered_news_items:
        grouped[n["ticker"]].append(n)

    print(f"Grouped into {len(grouped)} tickers: {list(grouped.keys())}")

    # Set up LLM for categorization (using gpt-4o for better instruction following)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Process each ticker
    merged_results = []
    errors = []

    for ticker, articles in grouped.items():
        print(f"\nProcessing ticker: {ticker} ({len(articles)} articles)")
        try:
            merged_json = _categorize_ticker_news(ticker, articles, llm)
            categories = merged_json.get("categories", [])
            if len(categories) == 0:
                print(f"⚠ Warning: No categories returned for {ticker}")
            merged_results.append(merged_json)
            print(f"✓ Processed {ticker}: {len(categories)} categories")
        except Exception as e:
            error_msg = f"Error processing {ticker}: {str(e)}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

    # Write merged results
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Successfully written {len(merged_results)} ticker results to {output_path}")
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    print(f"{'='*60}")

    return merged_results


def _run_async_safely(coro):
    """Run async function safely, handling event loop creation/cleanup."""
    try:
        # Check if we're already in an async context
        asyncio.get_running_loop()
        # If we get here, we're in an async context - shouldn't happen in sync function
        raise RuntimeError("Cannot run async function in async context - use await instead")
    except RuntimeError:
        # No running loop, safe to create one with asyncio.run()
        return asyncio.run(coro)


async def _generate_recommendations_async(
    news_items: List[Dict[str, Any]],
    pdf_path: Path,
    batch_size: int,
    total_batches: int,
    min_recommendations: int,
) -> List[Dict[str, Any]]:
    """
    Async version of recommendation generation that runs everything in a single event loop.
    This prevents event loop binding issues with RAGAnything workers.
    """
    all_recommendations = []
    
    # Initialize RAG instance ONCE in this event loop
    print("Initializing RAG instance (one-time setup)...")
    file_path = str(pdf_path.resolve())
    rag_instance = None
    try:
        rag_instance = await init_rag(file_path)
        print("✓ RAG instance initialized successfully\n")
    except Exception as e:
        print(f"✗ Failed to initialize RAG instance: {e}")
        print(f"  Error type: {type(e).__name__}")
        traceback.print_exc()
        print("\n⚠ Falling back to per-batch initialization (less efficient)...")
        rag_instance = None
    
    # Process batches in the same event loop
    for batch_num in range(0, len(news_items), batch_size):
        batch = news_items[batch_num:batch_num + batch_size]
        batch_num_display = (batch_num // batch_size) + 1
        
        batch_high = sum(1 for n in batch if n.get("rel", 0) >= 0.7)
        batch_med = sum(1 for n in batch if 0.5 <= n.get("rel", 0) < 0.7)
        batch_low = sum(1 for n in batch if 0.2 <= n.get("rel", 0) < 0.5)
        batch_min = batch_high * 4 + batch_med * 3 + batch_low * 2
        
        print(f"Processing batch {batch_num_display}/{total_batches}: {len(batch)} items")
        print(f"  High: {batch_high}, Medium: {batch_med}, Low: {batch_low}")
        print(f"  Expected: ~{batch_min} recommendations\n")
        
        formatted_batch = json.dumps(batch, separators=(',', ':'))
        formatted_prompt = RECOMMENDATION_PROMPT_TEMPLATE.format(
            batch_count=len(batch),
            batch_min_recommendations=batch_min,
            batch_num=batch_num_display,
            total_batches=total_batches,
            new=formatted_batch
        )
        
        try:
            # Use optimized path if RAG instance is available
            if rag_instance is not None:
                # Suppress RAGAnything cleanup warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*no current event loop.*")
                    warnings.filterwarnings("ignore", message=".*Failed to finalize.*")
                    # Reuse the same RAG instance for query (same event loop)
                    response = await query_rag(rag_instance, formatted_prompt)
            else:
                # Fallback: use ragmain() (creates new instance per batch - less efficient)
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*no current event loop.*")
                    warnings.filterwarnings("ignore", message=".*Failed to finalize.*")
                    response = await ragmain(formatted_prompt, file_path=file_path)
            
            if response is None:
                print(f"  ✗ Batch {batch_num_display} failed: RAG query returned None")
                continue
            
            # Normalize response to string
            if isinstance(response, list):
                if response:
                    all_recommendations.append(response)
                    print(f"  ✓ Batch {batch_num_display} completed: {len(response)} recommendations (list format)")
                else:
                    print(f"  ⚠ Batch {batch_num_display} returned empty list")
                continue
            elif not isinstance(response, str):
                response = str(response)
            
            # Debug: show response preview
            response_preview = response[:500] if len(response) > 500 else response
            print(f"  Response preview (first 500 chars): {response_preview}...")
            
            batch_rec_count = response.count('"client_name"')
            print(f"  ✓ Batch {batch_num_display} completed: {batch_rec_count} recommendations found in response")
            all_recommendations.append(response)
            
        except Exception as e:
            print(f"  ✗ Batch {batch_num_display} failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            traceback.print_exc()
            continue
    
    if rag_instance is not None:
        print(f"\n✓ RAG instance cleanup (will be garbage collected)")
    
    return all_recommendations


def generate_recommendations(
    merged_news_path: Path = MERGED_NEWS_PATH,
    output_path: Path = RECOMMENDATIONS_PATH,
    pdf_path: Path = PDF_PATH,
    batch_size: int = 6,
) -> List[Dict[str, Any]]:
    """
    Generate client recommendations from merged news using RAG.
    
    Args:
        merged_news_path: Path to merged_news.json
        output_path: Path to write recommendations (prety_recommendation.json)
        pdf_path: Path to client portfolio PDF for RAG
        batch_size: Number of news items to process per batch
    
    Returns:
        List of recommendation dictionaries
    """
    print("=" * 60)
    print("Generating client recommendations from merged news...")
    print("=" * 60)
    
    # Load merged news
    print(f"Loading merged news from {merged_news_path}...")
    with open(merged_news_path, "r", encoding="utf-8") as f:
        merged_news = json.load(f)
    
    # Flatten categorized news into compact list
    news_items = []
    for ticker_data in merged_news:
        ticker = ticker_data.get("ticker", "")
        categories = ticker_data.get("categories", [])
        
        for category in categories:
            topic = category.get("topic", "")
            summary = category.get("summary", "")
            sources = category.get("sources", [])
            
            # Ensure scores are floats (handle string conversion)
            relevance_score = category.get("relevance_score", 0)
            if isinstance(relevance_score, str):
                try:
                    relevance_score = float(relevance_score)
                except (ValueError, TypeError):
                    relevance_score = 0.0
            
            sentiment_score = category.get("sentiment_score", 0)
            if isinstance(sentiment_score, str):
                try:
                    sentiment_score = float(sentiment_score)
                except (ValueError, TypeError):
                    sentiment_score = 0.0
            
            # Convert to float if not already
            relevance_score = float(relevance_score) if relevance_score else 0.0
            sentiment_score = float(sentiment_score) if sentiment_score else 0.0
            
            news_item = {
                "t": ticker,
                "topic": topic,
                "sum": summary,
                "src": sources,
                "rel": relevance_score,
                "sent": sentiment_score,
            }
            news_items.append(news_item)
    
    if not news_items:
        print("⚠ WARNING: No news items found in merged_news.json")
        print("  This could mean:")
        print("  - merged_news.json is empty or malformed")
        print("  - All categories were filtered out")
        return []
    
    # Sort by relevance (highest first)
    news_items.sort(key=lambda x: x.get("rel", 0), reverse=True)
    
    # Count by relevance level
    high_rel = sum(1 for n in news_items if n.get("rel", 0) >= 0.7)
    med_rel = sum(1 for n in news_items if 0.5 <= n.get("rel", 0) < 0.7)
    low_rel = sum(1 for n in news_items if 0.2 <= n.get("rel", 0) < 0.5)
    
    print(f"\nProcessing {len(news_items)} news items:")
    print(f"  High relevance (>=0.7): {high_rel} items (target: 4-5 recommendations each)")
    print(f"  Medium relevance (0.5-0.7): {med_rel} items (target: 3-4 recommendations each)")
    print(f"  Standard relevance (0.2-0.5): {low_rel} items (target: 2-3 recommendations each)")
    
    min_recommendations = high_rel * 4 + med_rel * 3 + low_rel * 2
    print(f"  Expected total recommendations: ~{min_recommendations}\n")
    
    # Process in batches
    total_batches = (len(news_items) + batch_size - 1) // batch_size
    
    print(f"{'='*60}")
    print(f"Processing in batches of {batch_size} items to avoid timeouts...")
    print(f"{'='*60}\n")
    
    # OPTIMIZATION: Run all RAG operations in a single event loop
    # This prevents "bound to different event loop" errors by keeping workers in the same loop
    print("Running all batches in a single event loop to avoid worker binding issues...")
    all_recommendations = _run_async_safely(
        _generate_recommendations_async(
            news_items=news_items,
            pdf_path=pdf_path,
            batch_size=batch_size,
            total_batches=total_batches,
            min_recommendations=min_recommendations,
        )
    )
    
    # Combine all batch responses
    print(f"\n{'='*60}")
    print("Combining all batch results...")
    print(f"  Total batch responses to parse: {len(all_recommendations)}")
    print(f"{'='*60}\n")
    
    if not all_recommendations:
        print("⚠ WARNING: No batch responses to parse!")
        print("  This means all batches either failed or returned empty results.")
        print("  Check the batch processing logs above for errors.")
        # Write empty array
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []
    
    combined_recommendations = []
    
    for batch_idx, batch_resp in enumerate(all_recommendations, 1):
        print(f"Parsing batch response {batch_idx}/{len(all_recommendations)}...")
        if not isinstance(batch_resp, str):
            if isinstance(batch_resp, list):
                combined_recommendations.extend(batch_resp)
                continue
            batch_resp = str(batch_resp)
        
        # Strategy 1: Parse as JSON array
        try:
            cleaned = batch_resp.strip()
            if cleaned.startswith('```'):
                json_match = re.search(r'```(?:json|python)?\s*(\[.*?\])\s*```', cleaned, re.DOTALL)
                if json_match:
                    cleaned = json_match.group(1)
                else:
                    json_match = re.search(r'(\[.*\])', cleaned, re.DOTALL)
                    if json_match:
                        cleaned = json_match.group(1)
            
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                print(f"  ✓ Strategy 1 succeeded: parsed {len(parsed)} recommendations")
                combined_recommendations.extend(parsed)
                continue
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"  Strategy 1 failed: {type(e).__name__}")
            pass
        
        # Strategy 2: Extract JSON array with regex
        json_match = re.search(r'(\[[\s\S]*\])', batch_resp, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, list):
                    print(f"  ✓ Strategy 2 succeeded: parsed {len(parsed)} recommendations")
                    combined_recommendations.extend(parsed)
                    continue
            except json.JSONDecodeError as e:
                print(f"  Strategy 2 failed: JSONDecodeError - {str(e)[:100]}")
                pass
        
        # Strategy 3: Extract individual recommendation dicts
        dict_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*"client_name"(?:[^{}]|(?:\{[^{}]*\}))*\}'
        dict_matches = re.findall(dict_pattern, batch_resp, re.DOTALL)
        if dict_matches:
            print(f"  Trying Strategy 3: found {len(dict_matches)} potential recommendation dicts")
            parsed_count = 0
            for match in dict_matches:
                try:
                    rec_dict = json.loads(match)
                    if isinstance(rec_dict, dict) and "client_name" in rec_dict:
                        combined_recommendations.append(rec_dict)
                        parsed_count += 1
                except json.JSONDecodeError:
                    pass
            if parsed_count > 0:
                print(f"  ✓ Strategy 3 succeeded: parsed {parsed_count} recommendations")
                continue
        
        print(f"  ✗ All parsing strategies failed for batch {batch_idx}")
        print(f"  Response type: {type(batch_resp).__name__}, length: {len(str(batch_resp))}")
    
    # Validate and write results
    recommendation_count = len(combined_recommendations)
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS:")
    print(f"  Generated: {recommendation_count} recommendations")
    print(f"  Expected minimum: {min_recommendations} recommendations")
    if recommendation_count < min_recommendations * 0.7:
        print(f"  ⚠ WARNING: Only {recommendation_count} recommendations generated")
        print(f"     Expected at least {min_recommendations} (70% threshold: {int(min_recommendations * 0.7)})")
    else:
        print(f"  ✓ Successfully generated recommendations")
    print(f"{'='*60}\n")
    
    # Write to file
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        if combined_recommendations:
            json.dump(combined_recommendations, f, indent=2, ensure_ascii=False)
            print(f"✓ Wrote {len(combined_recommendations)} recommendations to {output_path}")
        else:
            json.dump([], f, indent=2)
            print(f"⚠ No recommendations parsed, wrote empty array to {output_path}")
    
    if combined_recommendations:
        print(f"\nSample recommendation (first of {len(combined_recommendations)}):")
        print(json.dumps(combined_recommendations[0], indent=2))
    
    return combined_recommendations


def fetch_and_score_yahoo_news(
    tickers: Optional[List[str]] = None,
    limit: int = 5,
    output_path: Path = PRETTY_NEWS_PATH,
) -> List[Dict[str, Any]]:
    """Fetch latest Yahoo news, score with LLM, and write to prety_news.json."""
    tickers = tickers or DEFAULT_TICKERS
    print(f"Fetching Yahoo Finance RSS for {len(tickers)} tickers...")
    batch = get_news_for_symbols(tickers, limit=limit)
    if not batch:
        raise RuntimeError("Yahoo Finance news fetch returned no data.")

    items = _flatten_news(batch)
    scored = score_news_with_llm(items)

    timestamp = datetime.utcnow().isoformat()
    payload = {
        "generated_at": timestamp,
        "source": "yahoo_finance_rss",
        "tickers": tickers,
        "items": scored,
    }

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)

    print(f"✓ Wrote {len(scored)} scored news items to {output_path}")
    return scored


def run_full_pipeline(
    tickers: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Complete pipeline: Fetch Yahoo news → Score → Categorize/Merge → Generate Recommendations
    
    Returns:
        Dict with 'scored' (list of scored items), 'merged' (list of merged ticker results),
        and 'recommendations' (list of client recommendations)
    """
    print("=" * 60)
    print("Starting full news pipeline: Fetch → Score → Merge → Generate Recommendations")
    print("=" * 60)
    
    # Step 1: Fetch and score
    print("\n[Step 1/3] Fetching and scoring Yahoo Finance news...")
    scored = fetch_and_score_yahoo_news(tickers=tickers, limit=limit)
    
    # Step 2: Categorize and merge
    print("\n[Step 2/3] Categorizing and merging news by ticker...")
    merged = categorize_and_merge_news()
    
    # Step 3: Generate recommendations
    print("\n[Step 3/3] Generating client recommendations...")
    recommendations = generate_recommendations()
    
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Scored items: {len(scored)}")
    print(f"  Merged tickers: {len(merged)}")
    print(f"  Recommendations: {len(recommendations)}")
    print("=" * 60)
    
    return {
        "scored": scored,
        "merged": merged,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    run_full_pipeline()

