from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.document_chunk import DocumentChunk
from app.services.embedding_pipeline import EmbeddingPipeline

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/trigger-embedding")
async def trigger_embedding(
    source_type: str = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger embedding for pending chunks."""
    pipeline = EmbeddingPipeline(db)

    if source_type and source_type not in ("resume", "jd", "question_bank"):
        raise HTTPException(status_code=400, detail="Invalid source_type")

    # Count pending chunks
    stmt = select(func.count(DocumentChunk.id)).where(
        DocumentChunk.tenant_id == tenant.id,
        DocumentChunk.embedding_status == "pending",
    )
    if source_type:
        stmt = stmt.where(DocumentChunk.source_type == source_type)

    result = await db.execute(stmt)
    count = result.scalar() or 0

    # Trigger via Celery
    pipeline.trigger_embedding_batch(source_type=source_type, tenant_id=str(tenant.id))

    return {
        "status": "triggered",
        "pending_chunks": count,
        "source_type": source_type or "all",
    }


@router.get("/embedding-status")
async def embedding_status(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get embedding progress statistics."""
    stmt = (
        select(DocumentChunk.source_type, DocumentChunk.embedding_status, func.count(DocumentChunk.id))
        .where(DocumentChunk.tenant_id == tenant.id)
        .group_by(DocumentChunk.source_type, DocumentChunk.embedding_status)
    )
    result = await db.execute(stmt)
    rows = result.all()

    stats = {}
    for source_type, status, count in rows:
        if source_type not in stats:
            stats[source_type] = {}
        stats[source_type][status] = count

    return {"tenant_id": str(tenant.id), "stats": stats}
