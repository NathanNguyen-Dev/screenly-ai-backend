from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
import logging
from datetime import datetime
from uuid import UUID

from ..dependencies import get_current_user
from ..models.job import JobCreate, JobRead, JobUpdate, LocationType, SeniorityLevel # Import Enums and JobUpdate
from ..db import get_db_connection
from firebase_admin import auth
import psycopg2
from psycopg2.extras import DictCursor # To get results as dictionaries

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["Jobs"],
    dependencies=[Depends(get_current_user)] # Protect all routes in this router
)

logger = logging.getLogger(__name__)

@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """
    Create a new job listing.
    Requires authenticated user.
    """
    logger.info(f"User {current_user.uid} attempting to create job: {job_in.title}")
    job_id = uuid.uuid4()
    created_at = datetime.utcnow()
    
    query = """
        INSERT INTO jobs (id, title, description, location, location_type, seniority_level, created_by_user_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, title, description, location, location_type, seniority_level, created_by_user_id, created_at;
    """
    values = (
        str(job_id),
        job_in.title,
        job_in.description,
        job_in.location,
        job_in.location_type.value if job_in.location_type else None, # Get Enum value or None
        job_in.seniority_level.value if job_in.seniority_level else None, # Get Enum value or None
        current_user.uid,
        created_at
    )
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                created_job_record = cur.fetchone()
                conn.commit()
                
                if not created_job_record:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                        detail="Failed to create job in database.")
                
                logger.info(f"Job created successfully with ID: {created_job_record['id']} by user {current_user.uid}")
                
                # Construct the response using the returned record
                response_job = JobRead(
                    id=created_job_record['id'],
                    title=created_job_record['title'],
                    description=created_job_record['description'],
                    location=created_job_record['location'],
                    location_type=created_job_record['location_type'], # Read directly from DB record
                    seniority_level=created_job_record['seniority_level'], # Read directly from DB record
                    created_by_user_id=created_job_record['created_by_user_id'],
                    created_at=created_job_record['created_at'],
                    candidate_count=0, 
                    average_score=None,
                    screening_link=None
                )
                return response_job

    except psycopg2.Error as e:
        logger.error(f"Database error creating job for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Database error occurred.")
    except Exception as e:
        logger.error(f"Unexpected error creating job for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="An unexpected error occurred.")

@router.get("/", response_model=List[JobRead])
def read_jobs(
    current_user: auth.UserRecord = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve job listings created by the current user, including candidate count.
    Requires authenticated user.
    """
    logger.info(f"User {current_user.uid} fetching jobs (skip={skip}, limit={limit})")

    # Query to fetch jobs and count candidates, removed j.updated_at
    query = """
        SELECT 
            j.id, j.title, j.description, j.location, 
            j.location_type, j.seniority_level, 
            j.created_by_user_id, j.created_at,
            COUNT(c.id) AS candidate_count
        FROM jobs j
        LEFT JOIN candidates c ON j.id = c.job_id
        WHERE j.created_by_user_id = %s 
        GROUP BY j.id, j.title, j.description, j.location, j.location_type, j.seniority_level, j.created_by_user_id, j.created_at
        ORDER BY j.created_at DESC
        LIMIT %s OFFSET %s;
    """
    values = (current_user.uid, limit, skip)

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                job_records = cur.fetchall()

                # Ensure JobRead model does not require updated_at if it's not selected
                jobs_list = [JobRead.model_validate(dict(row)) for row in job_records]
                
                logger.info(f"Found {len(jobs_list)} jobs for user {current_user.uid}")
                return jobs_list

    except psycopg2.Error as e:
        logger.error(f"Database error reading jobs for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database error occurred while fetching jobs.")
    except Exception as e:
        logger.error(f"Unexpected error reading jobs for user {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while fetching jobs.")

@router.get("/{job_id}", response_model=JobRead)
def read_job(
    job_id: UUID,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """
    Retrieve details for a specific job, including candidate count.
    Requires authenticated user who created the job.
    """
    logger.info(f"User {current_user.uid} fetching job details for job_id: {job_id}")

    # Query to fetch a specific job and its candidate count
    query = """
        SELECT 
            j.id, j.title, j.description, j.location, 
            j.location_type, j.seniority_level, 
            j.created_by_user_id, j.created_at,
            COUNT(c.id) AS candidate_count
        FROM jobs j
        LEFT JOIN candidates c ON j.id = c.job_id
        WHERE j.id = %s AND j.created_by_user_id = %s 
        GROUP BY j.id, j.title, j.description, j.location, j.location_type, j.seniority_level, j.created_by_user_id, j.created_at;
    """
    values = (str(job_id), current_user.uid)

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                job_record = cur.fetchone()

                if not job_record:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Job with ID {job_id} not found or not owned by user.")

                # Validate and return the job data
                return JobRead.model_validate(dict(job_record))

    except psycopg2.Error as e:
        logger.error(f"Database error reading job {job_id} for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database error occurred while fetching job details.")
    except Exception as e:
        logger.error(f"Unexpected error reading job {job_id} for user {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while fetching job details.")

@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """
    Update an existing job.
    Requires authenticated user who created the job.
    Only fields provided in the request body will be updated.
    """
    logger.info(f"User {current_user.uid} attempting to update job {job_id}")

    update_data = job_update.model_dump(exclude_unset=True) # Get only provided fields

    if not update_data:
        # If no data is provided for update, maybe fetch and return the existing job?
        # Or raise a 400 Bad Request error.
        # For simplicity, let's fetch and return the existing one.
        # Note: This requires a separate fetch or ensuring read_job logic is accessible.
        # Alternatively, raise an error if nothing to update.
        logger.warning(f"Update attempt for job {job_id} with no fields provided.")
        # Re-using read_job logic (ensure read_job doesn't cause infinite loop if called)
        # A better approach might be a dedicated fetch function.
        # Simplified: Raise error if nothing to update.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="No update data provided.")

    set_clauses = ["updated_at = NOW()"] # Always update the timestamp
    values = []

    # Dynamically build the SET part of the query
    for key, value in update_data.items():
        # Map model field names to DB column names if they differ (not needed here)
        column = key
        set_clauses.append(f"{column} = %s")
        # Handle Enums: store their string value
        if isinstance(value, (LocationType, SeniorityLevel)):
            values.append(value.value)
        else:
            values.append(value)
    
    set_query_part = ", ".join(set_clauses)
    
    # Add job_id and user_id for WHERE clause to the end of values list
    values.extend([str(job_id), current_user.uid])

    # Base query including RETURNING to get the updated data
    # Need to join with candidates to get candidate_count similar to read_job
    # This makes the query more complex. Alternatively, fetch separately after update.
    # Simpler approach first: Update, then fetch the full updated record.

    update_query = f"""
        UPDATE jobs
        SET {set_query_part}
        WHERE id = %s AND created_by_user_id = %s
        RETURNING id; -- Only check if update happened and ownership was correct
    """
    
    fetch_query = """
        SELECT 
            j.id, j.title, j.description, j.location, 
            j.location_type, j.seniority_level, 
            j.created_by_user_id, j.created_at, j.updated_at, -- Include updated_at
            COUNT(c.id) AS candidate_count
        FROM jobs j
        LEFT JOIN candidates c ON j.id = c.job_id
        WHERE j.id = %s AND j.created_by_user_id = %s 
        GROUP BY j.id, j.title, j.description, j.location, j.location_type, j.seniority_level, j.created_by_user_id, j.created_at, j.updated_at;
    """
    fetch_values = (str(job_id), current_user.uid)

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Execute the update
                cur.execute(update_query, tuple(values))
                updated_marker = cur.fetchone()
                
                if not updated_marker:
                     # This means the WHERE clause (id and owner) didn't match
                     # Or potentially the job was deleted between checks (less likely)
                    logger.warning(f"Update failed for job {job_id}. Not found or not owned by user {current_user.uid}.")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                        detail=f"Job with ID {job_id} not found or not owned by user.")

                # If update was successful, fetch the complete updated record
                cur.execute(fetch_query, fetch_values)
                updated_job_record = cur.fetchone()
                
                # Commit the transaction *after* successful fetch
                conn.commit()

                if not updated_job_record:
                    # Should not happen if update marker was returned, indicates logic error
                    logger.error(f"Failed to fetch job {job_id} after successful update marker.")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                        detail="Failed to retrieve updated job details.")

                logger.info(f"Job {job_id} updated successfully by user {current_user.uid}")
                
                # Validate and return the updated job
                # Ensure JobRead can handle the updated_at field if added
                return JobRead.model_validate(dict(updated_job_record))

    except psycopg2.Error as e:
        logger.error(f"Database error updating job {job_id} for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database error occurred while updating job.")
    except HTTPException as http_exc: # Re-raise specific HTTP exceptions
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error updating job {job_id} for user {current_user.uid}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while updating job.")

# DELETE endpoint can be added later
# @router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
# ... 