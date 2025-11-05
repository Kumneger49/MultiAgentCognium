

from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
import json
import re

from dotenv import load_dotenv
load_dotenv()

# --------------- LOAD NEWS DATA -----------------
file_path = "./prety_news.json"

with open(file_path, 'r') as f:
    news_items = json.load(f)

print(f"Loaded {len(news_items)} news items")

# --------------- FILTER OUT IRRELEVANT NEWS (relevance_score = 0) -----------------
filtered_news_items = [n for n in news_items if n.get("relevance_score", 0) != 0]
print(f"Filtered out {len(news_items) - len(filtered_news_items)} items with relevance_score = 0")
print(f"Processing {len(filtered_news_items)} relevant news items")

# --------------- GROUP NEWS BY TICKER -----------------
from collections import defaultdict

grouped = defaultdict(list)
for n in filtered_news_items:
    grouped[n["ticker"]].append(n)

print(f"Grouped into {len(grouped)} tickers: {list(grouped.keys())}")

# --------------- SET UP LLM -----------------
# Using gpt-4o for better instruction following and reduced hallucination
# If cost is a concern, you can switch back to "gpt-4o-mini"
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# --------------- PROMPT TEMPLATE -----------------
prompt = ChatPromptTemplate.from_template("""
You are a factual, neutral, and precise news summarizer and categorizer.

ABSOLUTE REQUIREMENT: You MUST use ONLY the articles provided below. Do NOT invent, hallucinate, or create any data that is not in the provided articles.

You will receive a JSON array of news articles for ticker {{ticker}}. Each article has:
- "title": the actual article title
- "summary": the actual article summary  
- "link": the actual article URL
- "source": the actual source domain
- "date": the publication date
- "relevance_score": relevance score (0.0 to 1.0) - already filtered to only include relevant articles
- "sentiment_score": sentiment score (-1.0 to 1.0) indicating positive/negative sentiment

Your tasks:
1. Read each article's title, summary, link, and source from the JSON below
2. Group articles that cover the same topic or event together
3. For each group, create an object with:
   - "topic": a short descriptive title based on the ACTUAL article titles/summaries
   - "summary": a 2-3 sentence summary based ONLY on the actual article summaries provided
   - "sources": a list where each object contains EXACTLY:
       - "name": copy the "source" field from the article
       - "title": copy the "title" field from the article
       - "link": copy the "link" field from the article
4. If an article is unique, it becomes its own category
5. You may skip articles with relevance_score < 0.2

CRITICAL: Every "name", "title", and "link" in your response MUST match exactly what is in the articles array below. Do NOT create fictional articles, titles, or links.

Return ONLY valid JSON with this exact structure:
{{
  "ticker": "{{ticker}}",
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

Ticker: {{ticker}}
Articles (copy the exact values from these):
{{articles}}
""")

# --------------- HELPER FUNCTION TO CLEAN JSON RESPONSE -----------------
def extract_json_from_response(text):
    """Extract JSON from LLM response, handling markdown code blocks"""
    # Remove markdown code blocks if present
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json or ``` at start
        text = re.sub(r'^```(?:json)?\s*', '', text)
        # Remove ``` at end
        text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    return text

# --------------- VALIDATION FUNCTION -----------------
def validate_response(merged_json, input_articles):
    """Validate that the response uses actual articles from input"""
    categories = merged_json.get("categories", [])
    
    # Create lookup maps from input articles (normalize for comparison)
    article_lookup = {}
    for art in input_articles:
        title = art.get("title", "").strip()
        link = art.get("link", "").strip()
        source = art.get("source", "").strip()
        
        # Normalize for matching
        title_norm = title.lower().strip()
        link_norm = link.lower().strip()
        
        # Store both title and link as keys pointing to the article
        if title_norm:
            article_lookup[title_norm] = art
        if link_norm:
            article_lookup[link_norm] = art
    
    invalid_sources = []
    valid_sources = []
    
    for cat in categories:
        sources = cat.get("sources", [])
        for source in sources:
            title = source.get("title", "").strip()
            link = source.get("link", "").strip()
            
            # Normalize for comparison
            title_norm = title.lower().strip()
            link_norm = link.lower().strip()
            
            # Check if title or link matches an input article
            title_match = title_norm in article_lookup
            link_match = link_norm in article_lookup
            
            if title_match or link_match:
                valid_sources.append(source)
            else:
                invalid_sources.append({
                    "category": cat.get("topic", "Unknown"),
                    "source": source,
                    "title": title,
                    "link": link
                })
    
    # If ALL sources are invalid, consider the whole response invalid
    # Otherwise, we'll clean up invalid ones later
    total_sources = len(valid_sources) + len(invalid_sources)
    if total_sources > 0 and len(valid_sources) == 0:
        return False, invalid_sources
    
    # If we have some valid sources, return True (we'll clean up invalid ones)
    return len(valid_sources) > 0, invalid_sources

# --------------- RUN PIPELINE -----------------
merged_results = []
errors = []

for ticker, articles in grouped.items():
    print(f"\nProcessing ticker: {ticker} ({len(articles)} articles)")
    
    try:
        # Format articles for the prompt - limit to first 20 articles to avoid token limits
        articles_to_process = articles[:20] if len(articles) > 20 else articles
        formatted_articles = json.dumps(articles_to_process, indent=2)
        
        # Debug: Check if articles are being formatted
        if len(formatted_articles) < 100:
            print(f"⚠ Warning: Articles string is very short ({len(formatted_articles)} chars). This might be an issue.")
            print(f"   First 200 chars: {formatted_articles[:200]}")
        else:
            print(f"   Articles formatted: {len(formatted_articles)} characters")
        
        # Build the prompt manually to ensure articles are included
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
        
        # Invoke directly with the prompt
        response = llm.invoke(prompt_text)
        
        # Extract and parse JSON
        response_text = response.content
        cleaned_response = extract_json_from_response(response_text)
        merged_json = json.loads(cleaned_response)
        
        # Validate the response
        if merged_json.get("ticker") != ticker:
            print(f"Warning: Response ticker {merged_json.get('ticker')} doesn't match input ticker {ticker}")
            merged_json["ticker"] = ticker
        
        # Post-process: Add scores to sources and categories if missing
        # Create lookup map from articles
        article_lookup = {}
        for art in articles_to_process:
            title = art.get("title", "").strip().lower()
            link = art.get("link", "").strip().lower()
            article_lookup[title] = art
            article_lookup[link] = art
        
        # Process categories to ensure scores are included
        for cat in merged_json.get("categories", []):
            # Calculate average scores from sources in this category
            relevance_scores = []
            sentiment_scores = []
            
            for source in cat.get("sources", []):
                title = source.get("title", "").strip().lower()
                link = source.get("link", "").strip().lower()
                
                # Find matching article
                matching_article = article_lookup.get(title) or article_lookup.get(link)
                
                if matching_article:
                    # Add scores to source if missing
                    if "relevance_score" not in source:
                        source["relevance_score"] = matching_article.get("relevance_score", 0)
                    if "sentiment_score" not in source:
                        source["sentiment_score"] = matching_article.get("sentiment_score", 0)
                    
                    # Collect scores for category average
                    relevance_scores.append(source.get("relevance_score", 0))
                    sentiment_scores.append(source.get("sentiment_score", 0))
            
            # Calculate and set category-level average scores
            if relevance_scores:
                if "relevance_score" not in cat or cat.get("relevance_score") is None:
                    cat["relevance_score"] = sum(relevance_scores) / len(relevance_scores)
                if "sentiment_score" not in cat or cat.get("sentiment_score") is None:
                    cat["sentiment_score"] = sum(sentiment_scores) / len(sentiment_scores)
        
        # Validate that sources match input articles
        is_valid, invalid_sources = validate_response(merged_json, articles_to_process)
        
        if not is_valid:
            print(f"⚠ Warning: Response contains {len(invalid_sources)} invalid sources")
            print(f"   Attempting to clean up response by removing invalid sources...")
            
            # Try to fix by removing invalid sources from categories
            cleaned_categories = []
            for cat in merged_json.get("categories", []):
                cleaned_sources = []
                for source in cat.get("sources", []):
                    title = source.get("title", "").strip().lower()
                    link = source.get("link", "").strip().lower()
                    
                    # Check if this source matches any input article
                    matches = False
                    for art in articles_to_process:
                        if (art.get("title", "").strip().lower() == title or 
                            art.get("link", "").strip().lower() == link):
                            matches = True
                            break
                    
                    if matches:
                        cleaned_sources.append(source)
                
                # Only keep categories that have at least one valid source
                if cleaned_sources:
                    cleaned_cat = cat.copy()
                    cleaned_cat["sources"] = cleaned_sources
                    cleaned_categories.append(cleaned_cat)
            
            if cleaned_categories:
                merged_json["categories"] = cleaned_categories
                print(f"   ✓ Cleaned up: {len(cleaned_categories)} categories with valid sources")
            else:
                # If all sources were invalid, try retry
                print(f"   All sources invalid. Retrying...")
                response = llm.invoke(prompt_text)
                response_text = response.content
                cleaned_response = extract_json_from_response(response_text)
                merged_json = json.loads(cleaned_response)
                merged_json["ticker"] = ticker
                
                # Re-validate
                is_valid, invalid_sources = validate_response(merged_json, articles_to_process)
                if not is_valid:
                    print(f"   Still having issues. Keeping response anyway (may contain some invalid data)")
        
        categories = merged_json.get("categories", [])
        if len(categories) == 0:
            print(f"⚠ Warning: No categories returned for {ticker}")
        merged_results.append(merged_json)
        print(f"✓ Processed {ticker}: {len(categories)} categories")
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing error for {ticker}: {str(e)}"
        print(f"✗ {error_msg}")
        if 'response_text' in locals():
            print(f"Response was: {response_text[:500]}")
        errors.append(error_msg)
    except Exception as e:
        error_msg = f"Error processing {ticker}: {str(e)}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)

# --------------- SAVE RESULTS -----------------
output_file = "./merged_news.json"
with open(output_file, 'w') as f:
    json.dump(merged_results, f, indent=2)

print(f"\n{'='*60}")
print(f"Successfully written {len(merged_results)} ticker results to {output_file}")
if errors:
    print(f"\nErrors encountered: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
print(f"{'='*60}")

# --------------- PRINT SUMMARY -----------------
print("\nSummary:")
for result in merged_results:
    ticker = result.get("ticker", "Unknown")
    categories = result.get("categories", [])
    print(f"  {ticker}: {len(categories)} categories")
    for cat in categories[:2]:  # Show first 2 categories
        print(f"    - {cat.get('topic', 'No topic')} ({len(cat.get('sources', []))} sources)")
