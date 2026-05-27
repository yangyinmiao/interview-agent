"""Celery tasks for async embedding processing."""

from app.tasks.celery_app import celery_app
from app.core.database import async_session_factory
from app.core.logging import get_structured_logger
from app.services.embedding_pipeline import EmbeddingPipeline
import asyncio

logger = get_structured_logger("tasks.embedding")


@celery_app.task(name="embed_source_chunks")
def embed_source_chunks(source_type: str, source_id: str):
    """Embed chunks for a specific document source."""
    logger.info(
        "Celery task started: embed_source_chunks",
        source_type=source_type,
        source_id=source_id,
    )

    async def _run():
        try:
            async with async_session_factory() as db:
                pipeline = EmbeddingPipeline(db)
                await pipeline.process_chunks(source_type=source_type, source_id=source_id)
                await db.commit()
        except Exception as e:
            logger.exception(
                "Embedding task failed",
                source_type=source_type,
                source_id=source_id,
                error=str(e),
            )
            raise

    asyncio.run(_run())


@celery_app.task(name="embed_all_pending")
def embed_all_pending(source_type: str = None, tenant_id: str = None):
    """Embed all pending chunks, optionally filtered by type or tenant."""
    logger.info(
        "Celery task started: embed_all_pending",
        source_type=source_type,
        tenant_id=tenant_id,
    )

    async def _run():
        try:
            async with async_session_factory() as db:
                pipeline = EmbeddingPipeline(db)
                await pipeline.process_all_pending(source_type=source_type, tenant_id=tenant_id)
                await db.commit()
        except Exception as e:
            logger.exception(
                "Batch embedding task failed",
                source_type=source_type,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    asyncio.run(_run())
