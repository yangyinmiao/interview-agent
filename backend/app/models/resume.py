import uuid
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base, TenantMixin, TimestampMixin


class Resume(Base, TenantMixin, TimestampMixin):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_url = Column(String(1000), nullable=False)
    raw_text = Column(Text, nullable=True)
    structured = Column(JSONB, nullable=True)
    parse_status = Column(String(20), default="pending")
