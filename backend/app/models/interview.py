import uuid
from sqlalchemy import Column, String, Integer, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base, TenantMixin


class Interview(Base, TenantMixin):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=True)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("jds.id"), nullable=True)
    question_bank_id = Column(UUID(as_uuid=True), ForeignKey("question_banks.id"), nullable=True)
    mode = Column(String(50), nullable=False, default="basic")
    status = Column(String(20), default="active")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Cached context — persisted across HTTP requests so resume/jd analysis
    # is computed once on start and reused every respond turn
    context_cache = Column(JSONB, nullable=True)
    follow_up_depth = Column(Integer, default=0)
