from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
import datetime

# Pydantic model for common candidate attributes
class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100, description="Candidate's full name")
    phone_number: str = Field(..., min_length=5, max_length=20, description="Candidate's phone number") # Consider more specific regex later
    email: Optional[EmailStr] = Field(None, description="Candidate's optional email address")

# Pydantic model for creating a new candidate (inherits from Base)
class CandidateCreate(CandidateBase):
    pass # No additional fields needed for creation beyond the base

# Pydantic model for reading candidate data from the DB (includes generated fields)
class CandidateRead(CandidateBase):
    id: UUID
    job_id: UUID # Foreign key relationship
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    status: str = Field('pending', description="Current status of the candidate screening")
    score: Optional[float] = Field(None, description="Screening score, if completed")

    class Config:
        from_attributes = True # Updated from orm_mode 