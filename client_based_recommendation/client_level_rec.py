
from cognium_codebase.main import main as ragmain
import asyncio
import json
import re
import os
from pathlib import Path

# Get the project root directory (where api.py is located)
# When running as a module, __file__ will be the script path
# We need to go up to the project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # Go up from client_based_recommendation/ to project root

# Load merged news with categorized articles and sources
merged_news_path = PROJECT_ROOT / "client_based_recommendation" / "merged_news.json"

prompt_template = """
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




def main():
    """Main function to generate client-level recommendations"""
    # Load merged news
    with open(str(merged_news_path), "r") as f:
        merged_news = json.load(f)

    # Flatten the categorized news into a compact list of news items with sources
    news_items = []
    for ticker_data in merged_news:
        ticker = ticker_data.get("ticker", "")
        categories = ticker_data.get("categories", [])
        
        for category in categories:
            topic = category.get("topic", "")
            summary = category.get("summary", "")
            sources = category.get("sources", [])
            relevance_score = category.get("relevance_score", 0)
            sentiment_score = category.get("sentiment_score", 0)
            
            # Format news item compactly with scores
            news_item = {
                "t": ticker,  # Shortened key
                "topic": topic,
                "sum": summary,  # Shortened key
                "src": sources,  # Shortened key - sources array
                "rel": relevance_score,  # Relevance score for prioritization
                "sent": sentiment_score  # Sentiment score
            }
            news_items.append(news_item)

    # Sort by relevance_score (highest first) to prioritize important news
    news_items.sort(key=lambda x: x.get("rel", 0), reverse=True)

    # Count news by relevance level
    high_rel = sum(1 for n in news_items if n.get("rel", 0) >= 0.7)
    med_rel = sum(1 for n in news_items if 0.5 <= n.get("rel", 0) < 0.7)
    low_rel = sum(1 for n in news_items if 0.2 <= n.get("rel", 0) < 0.5)

    print(f"Processing {len(news_items)} news items:")
    print(f"  High relevance (>=0.7): {high_rel} items (target: 4-5 recommendations each)")
    print(f"  Medium relevance (0.5-0.7): {med_rel} items (target: 3-4 recommendations each)")
    print(f"  Standard relevance (0.2-0.5): {low_rel} items (target: 2-3 recommendations each)")
    print(f"  Expected total recommendations: ~{high_rel*4 + med_rel*3 + low_rel*2}")

    # Calculate minimum expected recommendations
    min_recommendations = high_rel * 4 + med_rel * 3 + low_rel * 2

    # Split news items into batches to avoid timeouts
    BATCH_SIZE = 6  # Process 6 items per batch to avoid timeout
    all_recommendations = []

    print(f"\n{'='*60}")
    print(f"Processing in batches of {BATCH_SIZE} items to avoid timeouts...")
    print(f"{'='*60}\n")

    for batch_num in range(0, len(news_items), BATCH_SIZE):
        batch = news_items[batch_num:batch_num + BATCH_SIZE]
        batch_num_display = (batch_num // BATCH_SIZE) + 1
        total_batches = (len(news_items) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Count batch relevance levels
        batch_high = sum(1 for n in batch if n.get("rel", 0) >= 0.7)
        batch_med = sum(1 for n in batch if 0.5 <= n.get("rel", 0) < 0.7)
        batch_low = sum(1 for n in batch if 0.2 <= n.get("rel", 0) < 0.5)
        batch_min = batch_high * 4 + batch_med * 3 + batch_low * 2
        
        print(f"Processing batch {batch_num_display}/{total_batches}: {len(batch)} items")
        print(f"  High: {batch_high}, Medium: {batch_med}, Low: {batch_low}")
        print(f"  Expected: ~{batch_min} recommendations\n")
        
        # Format batch news compactly
        formatted_batch = json.dumps(batch, separators=(',', ':'))
        
        # Format prompt for this batch
        formated_news = prompt_template.format(
            batch_count=len(batch),
            batch_min_recommendations=batch_min,
            batch_num=batch_num_display,
            total_batches=total_batches,
            new=formatted_batch
        )
        
        try:
            # Use absolute path to ensure cache consistency (RAGAnything uses full path in cache key)
            file_path = str(PROJECT_ROOT / "client_based_recommendation" / "output.pdf")
            responce = asyncio.run(ragmain(formated_news, file_path=file_path))
            
            # Handle different return types from ragmain
            if responce is None:
                print(f"  ✗ Batch {batch_num_display} failed: ragmain returned None")
                continue
            
            # If response is already a list, convert to JSON string for parsing
            if isinstance(responce, list):
                responce = json.dumps(responce, ensure_ascii=False)
            elif not isinstance(responce, str):
                # Convert other types to string
                responce = str(responce)
            
            # Count recommendations in this batch
            batch_rec_count = responce.count('"client_name"')
            print(f"  ✓ Batch {batch_num_display} completed: {batch_rec_count} recommendations")
            # Debug: show first 300 chars of response to understand format
            print(f"  Response preview (first 300 chars): {responce[:300]}...")
            all_recommendations.append(responce)
                
        except Exception as e:
            import traceback
            print(f"  ✗ Batch {batch_num_display} failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            traceback.print_exc()
            # Continue with next batch
            continue

    # Combine all responses
    print(f"{'='*60}")
    print("Combining all batch results...")
    print(f"{'='*60}\n")

    # Combine responses - extract and merge recommendation lists
    combined_recommendations = []

    for batch_resp in all_recommendations:
        # Ensure batch_resp is a string
        if not isinstance(batch_resp, str):
            if isinstance(batch_resp, list):
                # If it's already a list, add directly
                combined_recommendations.extend(batch_resp)
                continue
            else:
                # Convert to string
                batch_resp = str(batch_resp)
        
        # Strategy 1: Try to parse the entire response as JSON (if LLM followed instructions)
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = batch_resp.strip()
            if cleaned.startswith('```'):
                # Extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json|python)?\s*(\[.*?\])\s*```', cleaned, re.DOTALL)
                if json_match:
                    cleaned = json_match.group(1)
                else:
                    # Try to find JSON array anywhere
                    json_match = re.search(r'(\[.*\])', cleaned, re.DOTALL)
                    if json_match:
                        cleaned = json_match.group(1)
            
            # Try parsing as JSON
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                combined_recommendations.extend(parsed)
                continue
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Strategy 2: Extract JSON array using regex (more lenient)
        json_match = re.search(r'(\[[\s\S]*\])', batch_resp, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, list):
                    combined_recommendations.extend(parsed)
                    continue
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Extract individual dicts and combine (fallback)
        # Use a more robust regex that handles nested structures
        dict_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*"client_name"(?:[^{}]|(?:\{[^{}]*\}))*\}'
        dict_matches = re.findall(dict_pattern, batch_resp, re.DOTALL)
        for match in dict_matches:
            try:
                rec_dict = json.loads(match)
                if isinstance(rec_dict, dict) and "client_name" in rec_dict:
                    combined_recommendations.append(rec_dict)
            except json.JSONDecodeError:
                pass

    # Validate response completeness
    recommendation_count = len(combined_recommendations) if combined_recommendations else 0
    try:
        print(f"\n{'='*60}")
        print(f"FINAL RESULTS:")
        print(f"  Generated: {recommendation_count} recommendations")
        print(f"  Expected minimum: {min_recommendations} recommendations")
        if recommendation_count < min_recommendations * 0.7:  # 70% threshold
            print(f"  ⚠ WARNING: Only {recommendation_count} recommendations generated")
            print(f"     Expected at least {min_recommendations} (70% threshold: {int(min_recommendations * 0.7)})")
        else:
            print(f"  ✓ Successfully generated recommendations")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"Could not validate response: {e}")

    # Write to JSON file (use absolute path to match API reading location)
    file_path_for_recommendation = PROJECT_ROOT / "prety_recommendation.json"

    with open(str(file_path_for_recommendation), "w", encoding="utf-8") as f:
        print("--------------------------------------------Writing recommendations to JSON file--------------------------------------------")
        if combined_recommendations:
            json.dump(combined_recommendations, f, indent=2, ensure_ascii=False)
            print(f"✓ Wrote {len(combined_recommendations)} recommendations to {file_path_for_recommendation}")
        else:
            # Fallback: write empty array if no recommendations were parsed
            json.dump([], f, indent=2)
            print(f"⚠ No recommendations parsed, wrote empty array to {file_path_for_recommendation}")
        print("--------------------------------------------Done writing to file--------------------------------------------")

    # Also print summary
    if combined_recommendations:
        print(f"\nSample recommendation (first of {len(combined_recommendations)}):")
        print(json.dumps(combined_recommendations[0], indent=2))


if __name__ == "__main__":
    main()