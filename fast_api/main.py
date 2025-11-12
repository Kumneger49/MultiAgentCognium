from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

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
            "/api/recommendations": "GET - Retrieve client recommendations",
            "/api/regenerate-recommendations": "POST - Trigger regeneration of recommendations",
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

@app.get("/api/recommendations")
async def get_recommendations():
    """
    Get client recommendations from prety_recommendation.json
    Returns the recommendations data as JSON
    """
    # Use absolute path relative to the base directory
    # Try both BASE_DIR (when mounted as file) and /app/data (when mounted as directory)
    recommendations_path = BASE_DIR / "prety_recommendation.json"
    if not recommendations_path.exists():
        # Fallback: check in /app/data if root is mounted as directory
        recommendations_path = Path("/app/data/prety_recommendation.json")
    
    try:
        # Check if file exists
        if not recommendations_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"prety_recommendation.json file not found at {recommendations_path}. Recommendations may not have been generated yet."
            )
        
        # Read and parse JSON file
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


def run_recommendation_generation() -> Dict[str, Any]:
    """
    Execute the recommendation generation script in the processor container using docker exec.
    Returns status information about the execution.
    
    We use docker exec directly since we know the container name (rag-agent-processor).
    This requires Docker CLI to be installed and Docker socket to be mounted.
    """
    try:
        # Use docker exec to run the script in the processor container
        # This works because:
        # 1. Docker socket is mounted at /var/run/docker.sock (in docker-compose.yml)
        # 2. Docker CLI is installed in the container
        # 3. Container name is fixed: rag-agent-processor
        result = subprocess.run(
            [
                "docker", "exec", "rag-agent-processor",
                "python", "-m", "client_based_recommendation.client_level_rec"
            ],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "message": "Recommendations generated successfully" if result.returncode == 0 else "Recommendation generation failed"
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Process timed out after 30 minutes",
            "message": "Recommendation generation timed out"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Docker CLI not found in container. Please ensure Docker CLI is installed.",
            "message": "Docker CLI not available"
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "message": f"Error executing recommendation generation: {str(e)}"
        }


@app.post("/api/regenerate-recommendations")
async def regenerate_recommendations(background_tasks: BackgroundTasks):
    """
    Trigger regeneration of client recommendations.
    This will run the client_level_rec.py script in the processor container using docker exec.
    
    Note: This is a long-running operation (can take several minutes).
    The endpoint will wait for the process to complete before returning.
    """
    try:
        # Check if processor container is running
        check_result = subprocess.run(
            ["docker", "ps", "--filter", "name=rag-agent-processor", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if "rag-agent-processor" not in check_result.stdout and "processor" not in check_result.stdout.lower():
            raise HTTPException(
                status_code=503,
                detail="Processor container (rag-agent-processor) is not running. Please start it with docker-compose up."
            )
        
        # Run the generation (this will block until complete)
        result = run_recommendation_generation()
        
        return {
            "status": "success" if result["success"] else "error",
            "message": result["message"],
            "details": {
                "returncode": result["returncode"],
                "stdout_preview": result["stdout"][:500] if result["stdout"] else "",
                "stderr_preview": result["stderr"][:500] if result["stderr"] else "",
            },
            "note": "Check /api/recommendations endpoint to see updated recommendations"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering recommendation generation: {str(e)}"
        )