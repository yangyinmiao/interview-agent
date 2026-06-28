import uuid
from sqlalchemy import Column, String, Text, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class InterviewMessage(Base):
    __tablename__ = "interview_messages"
    __table_args__ = (
        UniqueConstraint("interview_id", "request_id", name="uq_interview_message_request"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    request_id = Column(String(64), nullable=True)
    meta_data = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
