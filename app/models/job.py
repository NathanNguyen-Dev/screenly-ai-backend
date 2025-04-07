from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class JobBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="Title of the job posting")
    description: Optional[str] = Field(None, max_length=5000, description="Detailed description of the job")
    location: Optional[str] = Field(None, max_length=100, description="Job location (e.g., city, remote)") # Added location

class JobCreate(JobBase):
    # Inherits title, description, location
    pass

class JobRead(JobBase):
    id: uuid.UUID = Field(..., description="Unique identifier for the job")
    created_by_user_id: str = Field(..., description="Firebase UID of the user who created the job")
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    candidate_count: int = Field(0, description="Number of candidates associated with the job") # Add count
    average_score: Optional[float] = Field(None, description="Average screening score for candidates") # Add score
    screening_link: Optional[str] = Field(None, description="Public link for screening (if applicable)") # Add link

    class Config:
        orm_mode = True # For compatibility with ORMs or DB models later

# Model for updating a job (optional, can add later if needed)
# class JobUpdate(BaseModel):
#     title: Optional[str] = Field(None, min_length=3, max_length=100)
#     description: Optional[str] = Field(None, max_length=5000)
#     location: Optional[str] = Field(None, max_length=100) 