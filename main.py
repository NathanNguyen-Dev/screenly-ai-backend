import uvicorn
import os
from dotenv import load_dotenv
import logging

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials
# import json # No longer needed for this method

# Import the auth router
from app.routers import auth, jobs

# --- Early Initialization & Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables first
load_dotenv()
# Note: .env is still useful for FRONTEND_URL, DATABASE_URL etc.

# --- Firebase Initialization (Using File Path from Env Var - Local Dev Only!) ---
firebase_initialized = False
try:
    # Read the path to your service account key file from env var
    SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not SERVICE_ACCOUNT_PATH:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_PATH environment variable not set.")

    # Check if file exists before attempting to use it
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(f"Service account key file not found at path specified by FIREBASE_SERVICE_ACCOUNT_PATH: {SERVICE_ACCOUNT_PATH}")
        
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        logger.info(f"Firebase Admin SDK initialized successfully using file path from env var: {SERVICE_ACCOUNT_PATH}")
        firebase_initialized = True
    else:
        logger.info("Firebase Admin SDK already initialized.")
        firebase_initialized = True

except ValueError as e:
     logger.error(f"CRITICAL: Configuration error - {e}")
except FileNotFoundError as e:
     logger.error(f"CRITICAL: {e}. Make sure the service account file exists at the specified path.")
except Exception as e:
    logger.error(f"CRITICAL: Failed to initialize Firebase Admin SDK from file path in env var: {e}")

# --- FastAPI App Setup (Only if Firebase init seems okay or non-critical) ---
# You could wrap the rest of the setup in: if firebase_initialized:
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Screenly AI Backend",
    description="API for managing jobs, candidates, and AI screening calls.",
    version="0.1.0",
    # Add root path for Vercel deployment if needed
    # root_path="/api/v1" # Example if your frontend calls /api/v1/...
)

# CORS configuration
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    # Add production frontend URL from env var if available
    os.getenv("PRODUCTION_FRONTEND_URL", "")
]
origins = [origin for origin in origins if origin] # Filter out empty strings

if not origins:
    logger.warning("No CORS origins specified. Allowing all origins for local dev.")
    origins = ["*"] # Be cautious with this in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes --- 
app.include_router(auth.router)
app.include_router(jobs.router) # Include the jobs router

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Check the health of the API."""
    return {"status": "ok"}

# TODO: Add other API Routers (e.g., candidates)

# TODO: Add Authentication Dependencies
# TODO: Add API Routers (e.g., app.include_router(...))

# --- Uvicorn Runner --- 
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Uvicorn server on http://0.0.0.0:{port}")
    # Note: Running with `python main.py` might still cause import issues.
    # Recommend using `uvicorn main:app --reload --port 8000` from the terminal.
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 