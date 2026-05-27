from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResumeCreate(BaseModel):
    """Resume upload response."""
    pass


class ResumeResponse(BaseModel):
    id: str
    filename: str
    parse_status: str
    structured: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    analysis: Optional[dict] = None
    parse_status: str
