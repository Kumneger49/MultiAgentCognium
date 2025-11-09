from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pathlib import Path

# Get the base directory (parent of fast_api directory)
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI()


# Allow React frontend (localhost:3000) to access API

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 👈 in dev, allow all. In prod, restrict this.
    allow_origins=["*"],  # 👈 in dev, allow all. In prod, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_prety_news():
    """Lazy load prety_news.txt only when needed"""
    file_path = "./prety_news.txt"
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="prety_news.txt file not found")
        with open(file_path, "r") as f:
            text = json.load(f)
        return text
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in prety_news.txt: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading prety_news.txt: {str(e)}")

def format_prety_news(text):
    """Format the prety_news data"""
    edited_text = []
    for a in text:
        b = {
            "ticker": a["ticker"],
            "headline": a["title"],
            "summary": a["summary"],
            "link": a["link"],
            "sentiment": a["sentiment_score"],
            "tag": a["tag"]
        }
        edited_text.append(b)
    return edited_text

@app.get("/")
async def root():
    """API root endpoint - returns API information"""
    return {
        "message": "RAG Agent API",
        "endpoints": {
            "/api/merged-news": "GET - Retrieve categorized and merged news",
            "/docs": "API documentation (Swagger UI)",
            "/redoc": "API documentation (ReDoc)"
        }
    }

@app.get("/g")
def g():
    return "there is nothing here"

@app.get("/api/merged-news")
async def get_merged_news():
    """
    Get the categorized and merged news from merged_news.json
    Returns the full JSON structure with tickers, categories, and sources
    """
    # Use absolute path relative to the base directory
    merged_news_path = BASE_DIR / "client_based_recommendation" / "merged_news.json"
    
    try:
        # Check if file exists
        if not merged_news_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"merged_news.json file not found at {merged_news_path}"
            )
        
        # Read and parse JSON file
        with open(merged_news_path, 'r', encoding='utf-8') as f:
            merged_news = json.load(f)
        
        return {
            "status": "success",
            "data": merged_news,
            "count": len(merged_news) if isinstance(merged_news, list) else 1
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in merged_news.json: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading merged_news.json: {str(e)}")