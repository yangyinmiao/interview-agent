import uuid
from sqlalchemy import Column, String, Text, DateTime, func, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.models.base import Base, TenantMixin


class InterviewReport(Base, TenantMixin):
    __tablename__ = "interview_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), unique=True, nullable=False)
    overall_score = Column(Numeric(3, 1), nullable=True)
    scores = Column(JSONB, nullable=True)
    strengths = Column(ARRAY(Text), nullable=True)
    weaknesses = Column(ARRAY(Text), nullable=True)
    suggestions = Column(ARRAY(Text), nullable=True)
    raw_analysis = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
