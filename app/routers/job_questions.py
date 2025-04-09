from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import psycopg2
from psycopg2.extras import DictCursor
import logging
import uuid as uuid_pkg
from datetime import datetime

from ..models.job_question import JobQuestionCreate, JobQuestionRead
from ..dependencies import get_current_user
from ..db import get_db_connection
from firebase_admin import auth

router = APIRouter(
    prefix="/api/v1/jobs/{job_id}/questions", # Nested under jobs
    tags=["Job Questions"],
    dependencies=[Depends(get_current_user)] # Protect all routes
)

logger = logging.getLogger(__name__)

# Helper function to check job ownership (could be moved to dependencies)
def verify_job_ownership(job_id: UUID, user_id: str, db_conn):
    with db_conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT id FROM jobs WHERE id = %s AND created_by_user_id = %s", (str(job_id), user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Job with ID {job_id} not found or not owned by user.")

@router.get("/", response_model=List[JobQuestionRead])
def read_job_questions(
    job_id: UUID,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """Retrieve all questions for a specific job."""
    logger.info(f"User {current_user.uid} fetching questions for job {job_id}")
    query = """
        SELECT id, job_id, question_text, created_at, updated_at 
        FROM job_questions 
        WHERE job_id = %s 
        ORDER BY created_at ASC; -- Or by display_order if added
    """
    values = (str(job_id),)

    try:
        with get_db_connection() as conn:
            verify_job_ownership(job_id, current_user.uid, conn) # Removed await
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                records = cur.fetchall()
                questions = [JobQuestionRead.model_validate(dict(row)) for row in records]
                logger.info(f"Found {len(questions)} questions for job {job_id}")
                return questions
    except HTTPException as http_exc:
        raise http_exc # Re-raise ownership errors
    except psycopg2.Error as e:
        logger.error(f"DB error fetching questions for job {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error.")
    except Exception as e:
        logger.error(f"Unexpected error fetching questions for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error.")

@router.post("/", response_model=JobQuestionRead, status_code=status.HTTP_201_CREATED)
def create_job_question(
    job_id: UUID,
    question_data: JobQuestionCreate,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """Add a new question to a specific job."""
    logger.info(f"User {current_user.uid} adding question to job {job_id}")
    question_id = uuid_pkg.uuid4()
    query = """
        INSERT INTO job_questions (id, job_id, question_text)
        VALUES (%s, %s, %s)
        RETURNING id, job_id, question_text, created_at, updated_at;
    """
    values = (str(question_id), str(job_id), question_data.question_text)

    try:
        with get_db_connection() as conn:
            verify_job_ownership(job_id, current_user.uid, conn) # Removed await
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                record = cur.fetchone()
                conn.commit()
                if not record:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create question.")
                logger.info(f"Question {record['id']} added to job {job_id}")
                return JobQuestionRead.model_validate(dict(record))
    except HTTPException as http_exc:
        raise http_exc # Re-raise ownership errors
    except psycopg2.Error as e:
        logger.error(f"DB error adding question to job {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error.")
    except Exception as e:
        logger.error(f"Unexpected error adding question to job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error.")

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_question(
    job_id: UUID,
    question_id: UUID,
    current_user: auth.UserRecord = Depends(get_current_user)
):
    """Delete a specific question from a job."""
    logger.info(f"User {current_user.uid} deleting question {question_id} from job {job_id}")
    # Query ensures question belongs to the job and user owns the job
    query = """
        DELETE FROM job_questions q
        USING jobs j
        WHERE q.id = %s AND q.job_id = %s AND q.job_id = j.id AND j.created_by_user_id = %s
        RETURNING q.id;
    """
    values = (str(question_id), str(job_id), current_user.uid)

    try:
        with get_db_connection() as conn:
            # Ownership check is implicitly done by the DELETE query
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                deleted_record = cur.fetchone()
                conn.commit()
                if not deleted_record:
                    # If nothing was deleted, either question didn't exist, or job didn't belong to user
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found or not authorized.")
                logger.info(f"Question {question_id} deleted from job {job_id}")
                return # Return No Content
    except psycopg2.Error as e:
        logger.error(f"DB error deleting question {question_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting question {question_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error.") 