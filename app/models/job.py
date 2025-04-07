from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum

# Define Enums for the new fields
class LocationType(str, Enum):
    ON_SITE = "on-site"
    REMOTE = "remote"
    HYBRID = "hybrid"

class SeniorityLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID_LEVEL = "mid-level"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class JobBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="Title of the job posting")
    description: Optional[str] = Field(None, max_length=5000, description="Detailed description of the job")
    location: Optional[str] = Field(None, max_length=100, description="Specific location (e.g., city, area) if on-site/hybrid") 
    location_type: Optional[LocationType] = Field(None, description="Type of work location (on-site, remote, hybrid)")
    seniority_level: Optional[SeniorityLevel] = Field(None, description="Required seniority level for the job")

class JobCreate(JobBase):
    # Inherits all fields from JobBase
    pass

class JobRead(JobBase):
    id: uuid.UUID = Field(..., description="Unique identifier for the job")
    created_by_user_id: str = Field(..., description="Firebase UID of the user who created the job")
    created_at: datetime = Field(..., description="Timestamp when the job was created")
    candidate_count: int = Field(0, description="Number of candidates associated with the job")
    average_score: Optional[float] = Field(None, description="Average screening score for candidates")
    screening_link: Optional[str] = Field(None, description="Public link for screening (if applicable)")

    class Config:
        from_attributes = True
        use_enum_values = True

# Model for updating a job (optional, can add later if needed)
# class JobUpdate(BaseModel):
#     title: Optional[str] = Field(None, min_length=3, max_length=100)
#     description: Optional[str] = Field(None, max_length=5000)
#     location: Optional[str] = Field(None, max_length=100) 