from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class JDCreate(BaseModel):
    title: str
    company: Optional[str] = None
    description: str  # the raw job description text


class JDResponse(BaseModel):
    id: str
    filename: str
    title: Optional[str] = None
    company: Optional[str] = None
    parse_status: str
    structured: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JDAnalysisResponse(BaseModel):
    jd_id: str
    analysis: Optional[dict] = None
    parse_status: str
