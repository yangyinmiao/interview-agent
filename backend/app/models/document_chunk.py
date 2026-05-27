import uuid
from sqlalchemy import Column, String, Text, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base, TenantMixin


class DocumentChunk(Base, TenantMixin):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(20), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column("metadata", JSONB, nullable=True)
    embedding_status = Column(String(20), default="pending")
    qdrant_point_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
