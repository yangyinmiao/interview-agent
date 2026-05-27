from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JDResponse(BaseModel):
    id: str
    filename: str
    parse_status: str
    structured: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JDAnalysisResponse(BaseModel):
    jd_id: str
    analysis: Optional[dict] = None
    parse_status: str
