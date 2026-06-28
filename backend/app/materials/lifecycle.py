"""Own cleanup across every store used by Preparation Material."""

from __future__ import annotations

import uuid
from typing import Optional

from qdrant_client.models import PointIdsList
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.minio import get_minio
from app.core.qdrant import get_qdrant
from app.models.document_chunk import DocumentChunk


class PreparationMaterialLifecycle:
    """Delete one Preparation Material without leaving storage or vector debris."""

    def __init__(self, db: AsyncSession, *, qdrant=None, minio=None):
        self.db = db
        self.qdrant = qdrant or get_qdrant()
        self.minio = minio or get_minio()

    async def delete(
        self,
        *,
        tenant_id: str,
        source_type: str,
        source_id: str,
        object_name: Optional[str] = None,
    ) -> None:
        result = await self.db.execute(
            select(DocumentChunk).where(
                DocumentChunk.tenant_id == uuid.UUID(str(tenant_id)),
                DocumentChunk.source_type == source_type,
                DocumentChunk.source_id == uuid.UUID(str(source_id)),
            )
        )
        chunks = list(result.scalars().all())
        point_ids = [str(chunk.qdrant_point_id) for chunk in chunks if chunk.qdrant_point_id]
        if point_ids:
            collection = "questions" if source_type == "question_bank" else "chunks"
            self.qdrant.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=point_ids),
                wait=True,
            )

        if object_name:
            self.minio.remove_object(get_settings().minio_bucket, object_name)

        await self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.tenant_id == uuid.UUID(str(tenant_id)),
                DocumentChunk.source_type == source_type,
                DocumentChunk.source_id == uuid.UUID(str(source_id)),
            )
        )
