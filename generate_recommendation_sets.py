#!/usr/bin/env python3
"""
Generate 5 recommendation sets locally with intervals between runs.
Each run fetches fresh news and generates recommendations.
"""

import time
import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime

# Force mineru parser for local generation (more reliable)
os.environ["RAG_PARSER"] = "mineru"

# Suppress lightrag limit_async ERROR messages (harmless - workers from previous sets)
logging.getLogger("lightrag.utils").setLevel(logging.CRITICAL)
logging.getLogger("limit_async").setLevel(logging.CRITICAL)

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from client_based_recommendation.news_pipeline import run_full_pipeline
from cognium_codebase.main import clear_rag_cache

# Output directory for recommendation sets
OUTPUT_DIR = SCRIPT_DIR / "recommendation_sets"
OUTPUT_DIR.mkdir(exist_ok=True)

# Interval between runs (in seconds) - adjust as needed
INTERVAL_SECONDS = 300  # 5 minutes between runs

def generate_set(set_number: int):
    """Generate one recommendation set."""
    print("=" * 80)
    print(f"GENERATING RECOMMENDATION SET {set_number}/5")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Clear RAG instance cache from previous set to avoid event loop binding issues
    # This ensures each set creates a fresh RAG instance in its own event loop
    clear_rag_cache()
    
    try:
        # Run full pipeline (fetch → score → merge → generate)
        result = run_full_pipeline()
        
        # Load the generated recommendations
        recommendations_path = SCRIPT_DIR / "prety_recommendation.json"
        if not recommendations_path.exists():
            raise FileNotFoundError(f"Recommendations file not found: {recommendations_path}")
        
        with open(recommendations_path, "r", encoding="utf-8") as f:
            recommendations = json.load(f)
        
        # Save to set-specific file
        set_output_path = OUTPUT_DIR / f"recommendations_set_{set_number}.json"
        with open(set_output_path, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Set {set_number} generated successfully!")
        print(f"  Recommendations: {len(recommendations)}")
        print(f"  Saved to: {set_output_path}")
        print(f"  File size: {set_output_path.stat().st_size / 1024:.2f} KB")
        
        return True, len(recommendations)
        
    except Exception as e:
        print(f"\n✗ Set {set_number} failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def main():
    """Generate 5 recommendation sets with intervals."""
    print("=" * 80)
    print("LOCAL RECOMMENDATION SET GENERATION")
    print("=" * 80)
    print(f"Will generate 5 sets with {INTERVAL_SECONDS} second intervals")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    for set_num in range(1, 6):
        success, count = generate_set(set_num)
        results.append({
            "set_number": set_num,
            "success": success,
            "recommendation_count": count,
            "timestamp": datetime.now().isoformat()
        })
        
        # Wait before next run (except after last set)
        if set_num < 5:
            print(f"\n⏳ Waiting {INTERVAL_SECONDS} seconds before next run...")
            print(f"   (This ensures fresh news for set {set_num + 1})\n")
            time.sleep(INTERVAL_SECONDS)
    
    # Summary
    print("\n" + "=" * 80)
    print("GENERATION SUMMARY")
    print("=" * 80)
    successful = sum(1 for r in results if r["success"])
    total_recommendations = sum(r["recommendation_count"] for r in results)
    
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"{status} Set {result['set_number']}: {result['recommendation_count']} recommendations")
    
    print(f"\nSuccessful sets: {successful}/5")
    print(f"Total recommendations across all sets: {total_recommendations}")
    print(f"\nAll sets saved to: {OUTPUT_DIR}")
    print("=" * 80)
    
    # Save generation metadata
    metadata_path = OUTPUT_DIR / "generation_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_sets": 5,
            "successful_sets": successful,
            "results": results
        }, f, indent=2)
    
    print(f"\nMetadata saved to: {metadata_path}")

if __name__ == "__main__":
    main()

