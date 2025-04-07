from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
import logging
from datetime import datetime

from ..dependencies import get_current_user
from ..models.job import JobCreate, JobRead, LocationType, SeniorityLevel # Import Enums
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

# TODO: Add endpoints for GET /jobs/{job_id}, PUT /jobs/{job_id}, DELETE /jobs/{job_id} 