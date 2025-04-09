from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
import datetime

class JobQuestionBase(BaseModel):
    question_text: str = Field(..., min_length=5, max_length=1000, description="The text of the question")

class JobQuestionCreate(JobQuestionBase):
    pass

class JobQuestionRead(JobQuestionBase):
    id: UUID
    job_id: UUID
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True 