from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Import the recommendation generation function
from client_based_recommendation.client_level_rec import main as generate_recommendations

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
            "/api/recommendations": "GET - Retrieve client recommendations",
            "/api/regenerate-recommendations": "POST - Trigger regeneration of recommendations",
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
async def get_recommendations():
    """
    Get client recommendations from prety_recommendation.json
    Returns the recommendations data as JSON
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


@app.post("/api/regenerate-recommendations")
async def regenerate_recommendations(
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_api_key)  # Verify API key if configured
):
    """
    Trigger regeneration of client recommendations.
    This will run the client_level_rec.py script directly in this container.
    
    Note: This is a long-running operation (can take several minutes).
    The endpoint will wait for the process to complete before returning.
    """
    try:
        # Run the recommendation generation function directly
        # Since we're in the same container, we can import and call it directly
        print("Starting recommendation generation...")
        
        # Run the main function from client_level_rec.py
        # This is a synchronous function, so we run it in a thread pool to avoid blocking
        import concurrent.futures
        import traceback
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(generate_recommendations)
            try:
                # Wait for completion (with timeout)
                future.result(timeout=1800)  # 30 minute timeout
                print("Recommendation generation completed successfully")
                
                return {
                    "status": "success",
                    "message": "Recommendations generated successfully",
                    "note": "Check /api/recommendations endpoint to see updated recommendations"
                }
            except concurrent.futures.TimeoutError:
                return {
                    "status": "error",
                    "message": "Recommendation generation timed out after 30 minutes"
                }
            except Exception as e:
                error_msg = str(e)
                error_traceback = traceback.format_exc()
                print(f"Error during recommendation generation: {error_msg}")
                print(f"Traceback: {error_traceback}")
                return {
                    "status": "error",
                    "message": f"Error generating recommendations: {error_msg}",
                    "details": {
                        "error": error_msg[:500],  # First 500 chars of error
                        "traceback": error_traceback[:1000]  # First 1000 chars of traceback
                    }
                }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering recommendation generation: {str(e)}"
        )

