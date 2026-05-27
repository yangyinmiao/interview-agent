from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InterviewCreate(BaseModel):
    resume_id: Optional[str] = None
    jd_id: Optional[str] = None
    question_bank_id: Optional[str] = None
    mode: str = Field(default="basic", pattern="^(basic|deep|follow_up|stress)$")
    max_rounds: int = Field(default=10, ge=3, le=30)


class InterviewResponse(BaseModel):
    id: str
    mode: str
    status: str
    resume_id: Optional[str] = None
    jd_id: Optional[str] = None
    question_bank_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)


class QuestionResponse(BaseModel):
    question: str
    round_count: int
    max_rounds: int
    status: str  # 'active' | 'completed'


class InterviewMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterviewReportResponse(BaseModel):
    id: str
    interview_id: str
    overall_score: Optional[float] = None
    scores: Optional[dict] = None
    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    suggestions: Optional[list[str]] = None
    raw_analysis: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
