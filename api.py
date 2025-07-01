from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
import os
import json
import re
from datetime import datetime
import uuid
import traceback

# Import your existing modules
from main import main as prospect_main
from utility import FilteredProfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get desired profile count from environment variable
DEFAULT_DESIRED_PROFILES = int(os.getenv("desired_profile", "10"))

# Create FastAPI app
app = FastAPI(
    title="Prospect Research API",
    description="API for finding and analyzing key decision-makers in companies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class ProspectRequest(BaseModel):
    company: str
    search_term: Optional[str] = None
    max_profiles: Optional[int] = DEFAULT_DESIRED_PROFILES

class ProspectResponse(BaseModel):
    request_id: str
    status: str
    message: str
    profiles: Optional[List[Dict[str, Any]]] = None
    created_at: str
    completed_at: Optional[str] = None

class Profile(BaseModel):
    title: str
    url: str
    content: str
    score: float

class SearchStatusResponse(BaseModel):
    request_id: str
    status: str
    message: str
    profiles: List[Profile]
    created_at: str
    completed_at: Optional[str] = None

# In-memory storage for job status (use Redis/database in production)
job_status = {}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Prospect Research API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "default_max_profiles": DEFAULT_DESIRED_PROFILES
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "desired_profiles": DEFAULT_DESIRED_PROFILES
    }

@app.post("/prospect/search", response_model=ProspectResponse)
async def search_prospects(request: ProspectRequest, background_tasks: BackgroundTasks):
    """
    Search for prospects at a given company.
    
    This endpoint initiates a background search for key decision-makers
    at the specified company, focusing on R&D and digital transformation roles.
    """
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Set initial status
        job_status[request_id] = {
            "status": "processing",
            "message": "Search initiated",
            "profiles": None,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None
        }
        
        # Add background task (pass values directly, not via os.environ)
        background_tasks.add_task(
            process_prospect_search,
            request_id,
            request.company,
            request.search_term,
            request.max_profiles
        )
        
        return ProspectResponse(
            request_id=request_id,
            status="processing",
            message="Search initiated successfully. Use GET /prospect/status/{request_id} to check progress.",
            profiles=None,
            created_at=job_status[request_id]["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error initiating prospect search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate search: {str(e)}")

@app.get("/prospect/status/{request_id}", response_model=SearchStatusResponse)
async def get_search_status(request_id: str):
    """
    Get the status of a prospect search request.
    
    Returns the current status, progress, and results if completed.
    """
    if request_id not in job_status:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    job = job_status[request_id]
    
    # Parse profiles if they're in string format
    profiles = job["profiles"] or []
    
    if isinstance(profiles, str):
        try:
            # Handle markdown-wrapped JSON (```json ... ```)
            if profiles.startswith('```json') and profiles.endswith('```'):
                profiles = profiles[7:-3].strip()  # Remove ```json and ``` markers
            elif profiles.startswith('```') and profiles.endswith('```'):
                profiles = profiles[3:-3].strip()  # Remove ``` markers
            
            # Parse JSON string
            profiles = json.loads(profiles)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse profiles JSON for request {request_id}: {e}")
            profiles = []
    
    # Ensure profiles is a list and filter out any non-dict items
    if not isinstance(profiles, list):
        profiles = []
    
    valid_profiles = []
    for p in profiles:
        if isinstance(p, dict):
            # Ensure all required fields exist with defaults
            profile_dict = {
                "title": p.get("title", ""),
                "url": p.get("url", ""),
                "content": p.get("content", ""),
                "score": p.get("score", 0.0)
            }
            valid_profiles.append(profile_dict)
    
    return SearchStatusResponse(
        request_id=request_id,
        status=job["status"],
        message=job["message"],
        profiles=valid_profiles,
        created_at=job["created_at"],
        completed_at=job["completed_at"]
    )

@app.get("/prospect/list")
async def list_searches():
    """
    List all search requests and their statuses.
    """
    return {
        "searches": [
            {
                "request_id": req_id,
                "status": job["status"],
                "created_at": job["created_at"],
                "completed_at": job["completed_at"]
            }
            for req_id, job in job_status.items()
        ],
        "total": len(job_status)
    }

@app.delete("/prospect/{request_id}")
async def delete_search(request_id: str):
    """
    Delete a search request and its results.
    """
    if request_id not in job_status:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    del job_status[request_id]
    return {"message": f"Search request {request_id} deleted successfully"}

async def process_prospect_search(request_id: str, company: str, search_term: Optional[str], max_profiles: int):
    """
    Background task to process the prospect search.
    """
    try:
        logger.info(f"Starting prospect search for request {request_id}, company: {company}")
        
        # Update status
        job_status[request_id]["status"] = "processing"
        job_status[request_id]["message"] = "Searching for prospects..."
        
        # Run the prospect search with error handling
        try:
            # Call main() with arguments directly
            profiles = await prospect_main(company, max_profiles, search_term)
        except Exception as search_error:
            logger.error(f"Search error for request {request_id}: {str(search_error)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Check if it's a Pydantic compatibility error
            if "experimental_allow_partial" in str(search_error):
                error_msg = "Pydantic version compatibility issue detected. Please ensure you have the correct version of dependencies installed."
                logger.error(error_msg)
                
                # Update job status with specific error
                job_status[request_id].update({
                    "status": "error",
                    "message": f"Search failed due to dependency compatibility issue: {error_msg}",
                    "error": str(search_error),
                    "completed_at": datetime.now().isoformat()
                })
                return
            
            # For other errors, provide the original error message
            job_status[request_id].update({
                "status": "error",
                "message": f"Search failed: {str(search_error)}",
                "error": str(search_error),
                "completed_at": datetime.now().isoformat()
            })
            return
        
        # Process the profiles data
        if profiles:
            # Handle case where profiles is a string (JSON)
            if isinstance(profiles, str):
                try:
                    # Handle markdown-wrapped JSON
                    if profiles.startswith('```json') and profiles.endswith('```'):
                        profiles = profiles[7:-3].strip()
                    elif profiles.startswith('```') and profiles.endswith('```'):
                        profiles = profiles[3:-3].strip()
                    
                    profiles = json.loads(profiles)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse profiles JSON: {e}")
                    profiles = []
            
            # Ensure profiles is a list
            if not isinstance(profiles, list):
                profiles = []
            
            # Convert profiles to dict format for JSON serialization
            profile_dicts = []
            for profile in profiles:
                if isinstance(profile, FilteredProfile):
                    profile_dicts.append({
                        "title": profile.title,
                        "url": profile.url,
                        "content": profile.content,
                        "score": profile.score
                    })
                elif isinstance(profile, dict):
                    profile_dicts.append(profile)
            job_status[request_id]["profiles"] = profile_dicts

            # --- Append to {company_name}.json ---
            try:
                company_filename = f"{company.replace(' ', '_')}.json"
                with open(company_filename, "a", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "company": company,
                        "profiles": profile_dicts
                    }, f)
                    f.write("\n")
            except Exception as file_err:
                logger.error(f"Failed to write company data to file: {file_err}")
            # --- End append ---
        else:
            job_status[request_id]["profiles"] = []
        
        job_status[request_id]["status"] = "completed"
        job_status[request_id]["message"] = "Search completed successfully."
        job_status[request_id]["completed_at"] = datetime.now().isoformat()
    
    except Exception as e:
        logger.error(f"Error in background search for request {request_id}: {str(e)}")
        job_status[request_id]["status"] = "error"
        job_status[request_id]["message"] = f"Search failed: {str(e)}"
        job_status[request_id]["error"] = str(e)
        job_status[request_id]["completed_at"] = datetime.now().isoformat()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)