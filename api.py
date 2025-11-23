from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

# Import the full news pipeline (fetch → score → merge → generate recommendations)
from client_based_recommendation.news_pipeline import run_full_pipeline
from rotation_manager import RotationManager

# Get the base directory (project root)
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="RAG Agent API", version="1.0.0")

# CORS middleware - configurable via environment variable
# In development: ALLOWED_ORIGINS not set or "*" = allow all
# In production: Set ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_env == "*":
    allowed_origins = ["*"]
else:
    # Split comma-separated origins and strip whitespace
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication (optional - only enforced if API_KEY env var is set)
# In development: Don't set API_KEY = no authentication required
# In production: Set API_KEY="your-secret-key" = authentication required
API_KEY = os.getenv("API_KEY", None)
# Treat empty string as None (docker-compose may set empty string)
if API_KEY == "":
    API_KEY = None
security = HTTPBearer(auto_error=False)


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Verify API key from Authorization header.
    Only enforced if API_KEY environment variable is set (and not empty).
    """
    if API_KEY is None or API_KEY == "":
        # No API key configured - allow access (development mode)
        return True
    
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide it in Authorization header as: Bearer <your-api-key>"
        )
    
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return True


@app.get("/")
async def root():
    """API root endpoint - returns API information"""
    return {
        "message": "RAG Agent API",
        "endpoints": {
            "/api/merged-news": "GET - Retrieve categorized and merged news",
            "/api/recommendations": "GET - Retrieve client recommendations (all or filtered by client_id)",
            "/api/recommendations/client/{client_id}": "GET - Get recommendations for specific client (current set, no rotation)",
            "/api/regenerate-recommendations/client/{client_id}": "POST - Advance to next set with 60s delay (regenerate button)",
            "/api/regenerate-recommendations": "POST - Trigger actual regeneration with fresh news (fetches, scores, merges, generates)",
            "/api/generate-client-id": "GET - Generate a new client ID",
            "/docs": "API documentation (Swagger UI)",
            "/redoc": "API documentation (ReDoc)"
        }
    }


@app.get("/api/merged-news")
async def get_merged_news():
    """
    Get the categorized and merged news from merged_news.json
    Returns the full JSON structure with tickers, categories, and sources
    """
    merged_news_path = BASE_DIR / "client_based_recommendation" / "merged_news.json"
    
    try:
        if not merged_news_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"merged_news.json file not found at {merged_news_path}"
            )
        
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


@app.get("/api/recommendations")
async def get_recommendations(client_id: Optional[str] = Query(None, description="Optional: Filter recommendations for specific client")):
    """
    Get client recommendations from prety_recommendation.json
    
    If client_id is provided, returns recommendations for that client only.
    Otherwise, returns all recommendations.
    """
    recommendations_path = BASE_DIR / "prety_recommendation.json"
    
    try:
        if not recommendations_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"prety_recommendation.json file not found at {recommendations_path}. Recommendations may not have been generated yet."
            )
        
        with open(recommendations_path, 'r', encoding='utf-8') as f:
            recommendations = json.load(f)
        
        # Filter by client_id if provided
        if client_id:
            filtered = [r for r in recommendations if isinstance(r, dict) and r.get("client_name") == client_id]
            return {
                "status": "success",
                "client_id": client_id,
                "data": filtered,
                "count": len(filtered)
            }
        
        return {
            "status": "success",
            "data": recommendations,
            "count": len(recommendations) if isinstance(recommendations, list) else 1
        }
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in prety_recommendation.json: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading prety_recommendation.json: {str(e)}")


@app.get("/api/recommendations/client/{client_id}")
async def get_client_recommendations_with_rotation(client_id: str):
    """
    Get recommendations for a specific client using rotation system.
    
    This endpoint:
    1. Returns recommendations from the client's current set (1-5)
    2. Does NOT advance rotation (just shows current set)
    3. Returns ALL recommendations from the set (not filtered)
    
    New clients start at set 1. Use POST /api/regenerate-recommendations/client/{client_id} to advance to next set.
    Use GET /api/generate-client-id to get a new client_id if needed.
    """
    recommendations_dir = BASE_DIR / "recommendation_sets"
    rotation_state_file = BASE_DIR / "rotation_state.json"
    
    try:
        # Initialize rotation manager
        rotation_manager = RotationManager(
            state_file=rotation_state_file,
            num_sets=5
        )
        
        # Get current set for client (DO NOT advance - just show current set)
        set_number = rotation_manager.get_set_for_client(client_id, advance=False)
        
        # Load recommendations from the appropriate set
        set_file = recommendations_dir / f"recommendations_set_{set_number}.json"
        
        if not set_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation set {set_number} not found at {set_file}. Please upload recommendation sets first."
            )
        
        with open(set_file, 'r', encoding='utf-8') as f:
            all_recommendations = json.load(f)
        
        # Return ALL recommendations from the set (no filtering by client_name)
        return {
            "status": "success",
            "client_id": client_id,
            "set_number": set_number,
            "data": all_recommendations,
            "count": len(all_recommendations)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving client recommendations: {str(e)}"
        )


@app.get("/api/generate-client-id")
async def generate_client_id():
    """
    Generate a new client ID for users who don't have one.
    
    Returns a UUID that can be used as client_id in other endpoints.
    """
    client_id = str(uuid.uuid4())
    return {
        "status": "success",
        "client_id": client_id,
        "message": "Use this client_id in /api/recommendations/client/{client_id} and /api/regenerate-recommendations/client/{client_id}"
    }


def run_regeneration_pipeline():
    """
    Background task function to run the full news pipeline.
    This function will be executed in a background thread.
    """
    import traceback
    try:
        print("=" * 60)
        print("Starting full news pipeline: Fetch → Score → Merge → Generate Recommendations")
        print("=" * 60)
        
        # Run the complete pipeline (fetch fresh news, score, merge, generate recommendations)
        result = run_full_pipeline()
        
        print("=" * 60)
        print("Pipeline completed successfully!")
        print(f"  Scored items: {len(result.get('scored', []))}")
        print(f"  Merged tickers: {len(result.get('merged', []))}")
        print(f"  Recommendations: {len(result.get('recommendations', []))}")
        print("=" * 60)
        
    except Exception as e:
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"ERROR: Pipeline failed: {error_msg}")
        print(f"Traceback: {error_traceback}")
        # Log error but don't raise - background task should complete gracefully


@app.post("/api/regenerate-recommendations/client/{client_id}")
async def regenerate_client_recommendations(client_id: str):
    """
    Advance client to next recommendation set with simulated loading delay.
    
    This endpoint:
    1. Waits 5 seconds (simulates data loading)
    2. Advances client to next set (1 → 2 → 3 → 4 → 5 → 1)
    3. Returns all recommendations from the new set
    
    This is the "regenerate" button endpoint - it rotates through pre-generated sets.
    """
    recommendations_dir = BASE_DIR / "recommendation_sets"
    rotation_state_file = BASE_DIR / "rotation_state.json"
    
    try:
        # Wait 5 seconds to simulate loading
        await asyncio.sleep(5)
        
        # Initialize rotation manager
        rotation_manager = RotationManager(
            state_file=rotation_state_file,
            num_sets=5
        )
        
        # Advance client to next set
        set_number = rotation_manager.get_set_for_client(client_id, advance=True)
        
        # Load recommendations from the new set
        set_file = recommendations_dir / f"recommendations_set_{set_number}.json"
        
        if not set_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation set {set_number} not found at {set_file}. Please upload recommendation sets first."
            )
        
        with open(set_file, 'r', encoding='utf-8') as f:
            all_recommendations = json.load(f)
        
        # Return ALL recommendations from the new set
        return {
            "status": "success",
            "client_id": client_id,
            "set_number": set_number,
            "message": "Recommendations updated successfully",
            "data": all_recommendations,
            "count": len(all_recommendations)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error advancing client recommendations: {str(e)}"
        )


@app.post("/api/regenerate-recommendations")
async def regenerate_recommendations(
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_api_key)  # Verify API key if configured
):
    """
    Trigger regeneration of client recommendations with fresh news.
    
    This endpoint:
    1. Fetches latest Yahoo Finance news
    2. Scores news articles (relevance, sentiment)
    3. Categorizes and merges news by ticker
    4. Generates personalized client recommendations
    
    Note: This is a long-running operation (typically 5-10 minutes).
    The endpoint returns immediately. Poll /api/recommendations to check when new recommendations are ready.
    
    Note: This is for actual regeneration (runs the pipeline). For rotating through pre-generated sets,
    use POST /api/regenerate-recommendations/client/{client_id} instead.
    """
    try:
        # Add the pipeline to background tasks
        background_tasks.add_task(run_regeneration_pipeline)
        
        print("Regeneration pipeline queued in background...")
        
        return {
            "status": "processing",
            "message": "Fetching fresh news and generating recommendations. This may take 5-10 minutes.",
            "note": "Poll /api/recommendations endpoint to check when new recommendations are ready."
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering recommendation generation: {str(e)}"
        )



