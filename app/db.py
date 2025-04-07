import psycopg2
import os
from dotenv import load_dotenv
import logging
from contextlib import contextmanager

load_dotenv()
logger = logging.getLogger(__name__)

# Fetch the single DATABASE_URL environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("CRITICAL: DATABASE_URL environment variable not set.")
    # Consider raising an error or exiting if the DB is essential

@contextmanager
def get_db_connection():
    """Provides a database connection using the DATABASE_URL."""
    conn = None
    if not DATABASE_URL:
         logger.error("Database connection details incomplete in environment variables.")
         raise ValueError("Database connection details incomplete.")
         
    try:
        # Connect using the DATABASE_URL string
        conn = psycopg2.connect(DATABASE_URL)
        # Extract host for logging, be careful not to log password
        try:
            host_info = conn.get_dsn_parameters().get('host', 'unknown')
            logger.info(f"Database connection established to host {host_info}")
        except Exception:
             logger.info("Database connection established.") # Log generic message if host parse fails
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting DB connection: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

# Example usage (will be used in routers):
# with get_db_connection() as conn:
#     with conn.cursor() as cur:
#         cur.execute("SELECT version();")
#         db_version = cur.fetchone()
#         logger.info(f"PostgreSQL database version: {db_version}") 