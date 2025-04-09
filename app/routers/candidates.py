from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import psycopg2 # Use psycopg2
from psycopg2.extras import DictCursor # Use DictCursor
import logging
import uuid as uuid_pkg # Alias standard uuid library
from datetime import datetime

from ..models.candidate import CandidateCreate, CandidateRead
from ..dependencies import get_current_user # User auth dependency
from ..db import get_db_connection # Correct DB connection function
from firebase_admin import auth # Use firebase_admin.auth for UserRecord type hint

router = APIRouter(
    prefix="/api/v1/jobs/{job_id}/candidates",
    tags=["Candidates"],
    dependencies=[Depends(get_current_user)]
)

logger = logging.getLogger(__name__)

# --- API Endpoints ---

@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate_for_job(
    job_id: UUID,
    candidate_data: CandidateCreate,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """
    Create a new candidate associated with a specific job.
    Requires authentication.
    """
    # Optional: Add logic here to check if the current_user owns the job_id
    #           before allowing candidate creation. This requires fetching the job first.

    logger.info(f"User {current_user.uid} attempting to create candidate for job {job_id}")
    candidate_id = uuid_pkg.uuid4()
    created_at = datetime.utcnow()

    query = """
        INSERT INTO candidates (id, full_name, phone_number, email, job_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, full_name, phone_number, email, job_id, created_at, updated_at
    """
    values = (
        str(candidate_id),
        candidate_data.full_name,
        candidate_data.phone_number,
        candidate_data.email, # Pass None if optional email is not provided
        str(job_id), # Ensure job_id is passed as string if needed by DB/psycopg2
        created_at
    )

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Optional: Check if job_id exists and belongs to user first
                # cur.execute("SELECT id FROM jobs WHERE id = %s AND created_by_user_id = %s", (str(job_id), current_user.uid))
                # if cur.fetchone() is None:
                #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found or not owned by user.")

                cur.execute(query, values)
                created_candidate_record = cur.fetchone()
                conn.commit()

                if not created_candidate_record:
                     # This case should ideally not happen with RETURNING on INSERT
                     # unless there's a severe DB issue or misconfiguration.
                    logger.error(f"Failed to retrieve candidate record after insert for job {job_id}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                        detail="Failed to create candidate in database.")

                logger.info(f"Candidate {created_candidate_record['id']} created successfully for job {job_id} by user {current_user.uid}")

                # Convert DB record (DictRow) to dict before passing to Pydantic
                return CandidateRead.model_validate(dict(created_candidate_record))

    except psycopg2.errors.ForeignKeyViolation:
         # Catch specific error if the job_id doesn't exist
         logger.warning(f"Attempt to create candidate for non-existent job {job_id} by user {current_user.uid}")
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Job with ID {job_id} not found.")
    except psycopg2.Error as e:
        # Generic database error handling
        logger.error(f"Database error creating candidate for job {job_id}, user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected database error occurred while creating the candidate.")
    except Exception as e:
        # Catch-all for other unexpected errors
        logger.error(f"Unexpected error creating candidate for job {job_id}, user {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while creating the candidate.")

@router.get("/", response_model=List[CandidateRead])
def read_candidates_for_job(
    job_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """
    Retrieve candidates associated with a specific job.
    Requires authentication. Ensures user owns the job.
    """
    logger.info(f"User {current_user.uid} fetching candidates for job {job_id} (skip={skip}, limit={limit})")

    # First, verify the user owns the job (important for security)
    job_check_query = "SELECT id FROM jobs WHERE id = %s AND created_by_user_id = %s"
    job_check_values = (str(job_id), current_user.uid)

    # Query to fetch candidates
    candidate_query = """
        SELECT id, full_name, phone_number, email, job_id, created_at, updated_at, status, score
        FROM candidates
        WHERE job_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
    """
    candidate_values = (str(job_id), limit, skip)

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Check job ownership
                cur.execute(job_check_query, job_check_values)
                if cur.fetchone() is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Job with ID {job_id} not found or not owned by user.")

                # Fetch candidates
                cur.execute(candidate_query, candidate_values)
                candidate_records = cur.fetchall()

                # Validate and return candidate data
                # Ensure CandidateRead model includes status and score fields
                candidates_list = [CandidateRead.model_validate(dict(row)) for row in candidate_records]

                logger.info(f"Found {len(candidates_list)} candidates for job {job_id}, user {current_user.uid}")
                return candidates_list

    except psycopg2.Error as e:
        logger.error(f"Database error reading candidates for job {job_id}, user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database error occurred while fetching candidates.")
    except Exception as e:
        logger.error(f"Unexpected error reading candidates for job {job_id}, user {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while fetching candidates.")

# Add other candidate endpoints here later (GET candidate detail, PUT, DELETE)
# e.g., GET /api/v1/candidates/candidate/{candidate_id} to get a specific candidate
# e.g., PUT /api/v1/candidates/candidate/{candidate_id} to update a candidate
# e.g., DELETE /api/v1/candidates/candidate/{candidate_id} to delete a candidate 