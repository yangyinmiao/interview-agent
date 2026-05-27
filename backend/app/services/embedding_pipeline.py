"""Embedding pipeline: PG chunks → Embed → Qdrant."""

import time
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.document_chunk import DocumentChunk
from app.services.llm_factory import get_embeddings
from app.core.qdrant import get_qdrant
from app.core.logging import get_structured_logger
from qdrant_client.models import PointStruct

logger = get_structured_logger("services.embedding")


class EmbeddingPipeline:
    """Manages the embedding lifecycle for document chunks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()
        self.qdrant = get_qdrant()

    async def save_chunks(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str,
        chunks: List[dict],
    ):
        """Save document chunks to PostgreSQL."""
        for chunk_data in chunks:
            chunk = DocumentChunk(
                tenant_id=uuid.UUID(tenant_id),
                source_type=source_type,
                source_id=uuid.UUID(source_id),
                chunk_index=chunk_data["index"],
                content=chunk_data["content"],
                embedding_status="pending",
            )
            self.db.add(chunk)
        await self.db.flush()

        logger.info(
            f"Saved {len(chunks)} chunks to PG",
            source_type=source_type,
            source_id=source_id,
            chunk_count=len(chunks),
        )

    def trigger_embedding(self, source_type: str, source_id: str):
        """Trigger async embedding via Celery task."""
        from app.tasks.embedding_tasks import embed_source_chunks
        logger.info(
            "Triggering async embedding",
            source_type=source_type,
            source_id=source_id,
        )
        embed_source_chunks.delay(source_type=source_type, source_id=str(source_id))

    def trigger_embedding_batch(self, source_type: Optional[str] = None, tenant_id: Optional[str] = None):
        """Trigger batch embedding for all pending chunks."""
        from app.tasks.embedding_tasks import embed_all_pending
        logger.info(
            "Triggering batch embedding",
            source_type=source_type,
            tenant_id=tenant_id,
        )
        embed_all_pending.delay(source_type=source_type, tenant_id=tenant_id)

    async def process_chunks(
        self,
        source_type: str,
        source_id: str,
        batch_size: int = 20,
    ):
        """Process embedding for pending chunks of a specific source."""
        start = time.time()

        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.source_type == source_type,
                DocumentChunk.source_id == uuid.UUID(source_id),
                DocumentChunk.embedding_status == "pending",
            )
            .order_by(DocumentChunk.chunk_index)
        )
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            logger.debug("No pending chunks to embed", source_type=source_type, source_id=source_id)
            return

        total_chunks = len(chunks)
        logger.info(
            "Processing embedding",
            source_type=source_type,
            source_id=source_id,
            total_chunks=total_chunks,
            batch_size=batch_size,
        )

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i: i + batch_size]
            texts = [c.content for c in batch]

            vectors = self.embeddings.embed_documents(texts)

            points = []
            for chunk, vector in zip(batch, vectors):
                point_id = uuid.uuid4()
                points.append(
                    PointStruct(
                        id=str(point_id),
                        vector=vector,
                        payload={
                            "tenant_id": str(chunk.tenant_id),
                            "source_type": chunk.source_type,
                            "source_id": str(chunk.source_id),
                            "chunk_id": str(chunk.id),
                            "content": chunk.content,
                            "chunk_index": chunk.chunk_index,
                        },
                    )
                )
                chunk.embedding_status = "completed"
                chunk.qdrant_point_id = point_id

            collection_name = "questions" if source_type == "question_bank" else "chunks"
            self.qdrant.upsert(collection_name=collection_name, points=points)

        await self.db.flush()

        logger.info(
            "Embedding completed",
            source_type=source_type,
            source_id=source_id,
            total_chunks=total_chunks,
            duration_ms=round((time.time() - start) * 1000, 2),
        )

    async def process_all_pending(
        self,
        source_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Process all pending chunks, optionally filtered."""
        start = time.time()

        stmt = select(DocumentChunk).where(
            DocumentChunk.embedding_status == "pending"
        )
        if source_type:
            stmt = stmt.where(DocumentChunk.source_type == source_type)
        if tenant_id:
            stmt = stmt.where(DocumentChunk.tenant_id == uuid.UUID(tenant_id))
        stmt = stmt.order_by(DocumentChunk.created_at)

        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            logger.info("No pending chunks to embed in batch")
            return

        total_chunks = len(chunks)
        logger.info(
            "Processing batch embedding",
            total_chunks=total_chunks,
            source_type=source_type,
            tenant_id=tenant_id,
        )

        chunk_ids_by_source = {}
        for chunk in chunks:
            key = (chunk.source_type, str(chunk.source_id))
            if key not in chunk_ids_by_source:
                chunk_ids_by_source[key] = []
            chunk_ids_by_source[key].append(chunk)

        for (src_type, src_id), src_chunks in chunk_ids_by_source.items():
            for i in range(0, len(src_chunks), 20):
                batch = src_chunks[i: i + 20]
                texts = [c.content for c in batch]
                vectors = self.embeddings.embed_documents(texts)

                points = []
                for chunk, vector in zip(batch, vectors):
                    point_id = uuid.uuid4()
                    points.append(
                        PointStruct(
                            id=str(point_id),
                            vector=vector,
                            payload={
                                "tenant_id": str(chunk.tenant_id),
                                "source_type": chunk.source_type,
                                "source_id": str(chunk.source_id),
                                "chunk_id": str(chunk.id),
                                "content": chunk.content,
                            },
                        )
                    )
                    chunk.embedding_status = "completed"
                    chunk.qdrant_point_id = point_id

                collection_name = "questions" if src_type == "question_bank" else "chunks"
                self.qdrant.upsert(collection_name=collection_name, points=points)

        await self.db.flush()

        logger.info(
            "Batch embedding completed",
            total_chunks=total_chunks,
            duration_ms=round((time.time() - start) * 1000, 2),
        )
