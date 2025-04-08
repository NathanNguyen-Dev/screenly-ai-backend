import uvicorn
import os
from dotenv import load_dotenv
import logging
import json # Needed for parsing potential JSON strings if used

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials

# Import the auth router
from app.routers import auth, jobs, candidates

# --- Early Initialization & Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables first
load_dotenv()
# Note: .env is still useful for FRONTEND_URL, DATABASE_URL etc.

# --- Firebase Initialization (Using Environment Variables) ---
firebase_initialized = False
try:
    # Check for essential Firebase credential variables
    required_vars = [
        'FIREBASE_TYPE', 'FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY_ID',
        'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL', 'FIREBASE_CLIENT_ID',
        'FIREBASE_AUTH_URI', 'FIREBASE_TOKEN_URI', 'FIREBASE_AUTH_PROVIDER_X509_CERT_URL',
        'FIREBASE_CLIENT_X509_CERT_URL'
    ]
    if not all(os.getenv(var) for var in required_vars):
        missing = [var for var in required_vars if not os.getenv(var)]
        raise ValueError(f"Missing required Firebase environment variables: {', '.join(missing)}")

    # Construct the credential dictionary from environment variables
    private_key = os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n') # Replace literal \n with actual newlines
    
    firebase_credentials = {
        "type": os.getenv('FIREBASE_TYPE'),
        "project_id": os.getenv('FIREBASE_PROJECT_ID'),
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": private_key,
        "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
        "auth_uri": os.getenv('FIREBASE_AUTH_URI'),
        "token_uri": os.getenv('FIREBASE_TOKEN_URI'),
        "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
        # Add universe_domain if needed and set in env vars
        # "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com') 
    }

    cred = credentials.Certificate(firebase_credentials)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully using environment variables.")
        firebase_initialized = True
    else:
        logger.info("Firebase Admin SDK already initialized.")
        firebase_initialized = True

except ValueError as e:
     logger.error(f"CRITICAL: Configuration error - {e}")
# Removed FileNotFoundError as we are not loading from path anymore
except Exception as e:
    logger.error(f"CRITICAL: Failed to initialize Firebase Admin SDK from environment variables: {e}", exc_info=True)

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
app.include_router(candidates.router) # Include the candidates router

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