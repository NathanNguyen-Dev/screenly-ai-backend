# screenly-ai-backend

Backend API for Screenly AI, an AI-powered phone screening platform.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (via Supabase)
- **Authentication:** Firebase Admin SDK (for verifying frontend tokens)
- **Libraries:** Pydantic, psycopg2-binary, python-dotenv, uvicorn

## Setup & Running

1.  Ensure Python 3.10+ and pip are installed.
2.  Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file based on `.env.example` (if provided) or set environment variables:
    *   `DATABASE_URL`: Your Supabase PostgreSQL connection string.
    *   `FIREBASE_SERVICE_ACCOUNT_PATH`: Path to your Firebase Admin SDK service account JSON file.
    *   `FRONTEND_URL`: The URL of your frontend application (for CORS).
5.  Run the development server:
    ```bash
    uvicorn main:app --reload --port 8000
    ```

## API Documentation

API documentation (Swagger UI) is available at `/docs` when the server is running.
