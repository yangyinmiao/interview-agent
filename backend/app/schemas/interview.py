from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class InterviewCreate(BaseModel):
    resume_id: Optional[UUID] = None
    jd_id: Optional[UUID] = None
    question_bank_id: Optional[UUID] = None
    mode: str = Field(default="basic", pattern="^(basic|deep|follow_up|stress)$")
    max_rounds: int = Field(default=10, ge=3, le=30)


class InterviewResponse(BaseModel):
    id: str
    mode: str
    status: str
    resume_id: Optional[str] = None
    jd_id: Optional[str] = None
    question_bank_id: Optional[str] = None
    max_rounds: int = 10
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BatchDeleteInterviews(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)
    request_id: Optional[str] = Field(default=None, min_length=1, max_length=64)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class ReferenceAnswerResponse(BaseModel):
    message_id: str
    reference_answer: str
    cached: bool = False  # True if already generated before


class ProgressPoint(BaseModel):
    interview_id: str
    completed_at: datetime
    overall_score: Optional[float] = None
    scores: dict = Field(default_factory=dict)


class TopicProgress(BaseModel):
    topic: str
    attempts: int
    average_score: float
    latest_score: float
    change: Optional[float] = None


class ProgressTrendResponse(BaseModel):
    interviews: list[ProgressPoint]
    completed_count: int
    overall_change: Optional[float] = None
    dimension_changes: dict[str, float] = Field(default_factory=dict)
    topics: list[TopicProgress] = Field(default_factory=list)
