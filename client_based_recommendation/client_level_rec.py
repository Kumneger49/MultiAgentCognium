


from cognium_codebase.main import main as ragmain
import asyncio
import json
import re

# Load merged news with categorized articles and sources
merged_news_path = "./client_based_recommendation/merged_news.json"

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

Output: Python list of dicts with keys:
- "news": "Topic: [topic]\\nSummary: [sum]" (from data)
- "sources": use exact "src" array from data
- "client_name": "..."
- "recommendation": "2 sentences connecting all 3 factors"
- "rate_of_return": "estimate with % (e.g., 3-5% increase)"
- "portfolio_risk": "estimate with % (e.g., 8% decline)"
- "bank_commissions": "estimate with % (e.g., 2-3% growth)"

CRITICAL: Process ALL {batch_count} news items below. Do not stop after a few items.

News items (batch {batch_num}/{total_batches}, sorted by relevance - process ALL {batch_count}):
{new}
"""




# Load merged news
with open(merged_news_path, "r") as f:
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
        responce = asyncio.run(ragmain(formated_news, file_path="/Users/kumnegermatewos/Desktop/Cognium/Codebase/RagAgent/working/client_based_recommendation/output.pdf"))
        
        # Count recommendations in this batch
        batch_rec_count = responce.count('"client_name"')
        print(f"  ✓ Batch {batch_num_display} completed: {batch_rec_count} recommendations\n")
        all_recommendations.append(responce)
            
    except Exception as e:
        print(f"  ✗ Batch {batch_num_display} failed: {e}\n")
        # Continue with next batch
        continue

# Combine all responses
print(f"{'='*60}")
print("Combining all batch results...")
print(f"{'='*60}\n")

# Combine responses - extract and merge recommendation lists
combined_recommendations = []

for batch_resp in all_recommendations:
    # Try to extract the recommendations list
    list_match = re.search(r'\[(.*?)\]', batch_resp, re.DOTALL)
    if list_match:
        try:
            # Try to parse as JSON/Python list
            recommendations_text = list_match.group(0)
            # Extract individual recommendation dicts
            dict_matches = re.findall(r'\{[^{}]*"client_name"[^{}]*\}', recommendations_text, re.DOTALL)
            for match in dict_matches:
                try:
                    # Try to parse each dict
                    rec_dict = json.loads(match)
                    combined_recommendations.append(rec_dict)
                except:
                    pass
        except:
            pass

# If we couldn't parse, just combine the text
if not combined_recommendations:
    responce = "\n\n".join(all_recommendations)
else:
    # Format as Python list
    responce = "```python\nrecommendations = " + json.dumps(combined_recommendations, indent=4) + "\n```"

# Validate response completeness
try:
    recommendation_count = responce.count('"client_name"')
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

file_path_for_recommendation = "./prety_recommendation.txt"

with open(file_path_for_recommendation, "w") as f:
    print("--------------------------------------------Writing responce to file--------------------------------------------")
    f.write(responce)
    print("--------------------------------------------Done writing to file--------------------------------------------")

print(responce)