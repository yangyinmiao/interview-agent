from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.jd import JD
from app.schemas.jd import JDResponse, JDAnalysisResponse, JDCreate
from app.services.document_parser import DocumentParser
from app.services.embedding_pipeline import EmbeddingPipeline
from app.agents.jd_agent import JDAgent

router = APIRouter(prefix="/jds", tags=["jds"])


@router.post("", response_model=JDResponse, status_code=status.HTTP_201_CREATED)
async def create_jd(
    data: JDCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    jd = JD(
        tenant_id=tenant.id,
        title=data.title,
        company=data.company,
        filename=data.title,
        file_url="",
        raw_text=data.description,
        parse_status="parsed",
    )
    db.add(jd)
    await db.flush()

    from app.services.document_parser import Chunker
    pipeline = EmbeddingPipeline(db)
    chunker = Chunker()
    chunks = chunker.chunk(data.description, "jd")
    await pipeline.save_chunks(
        tenant_id=str(tenant.id),
        source_type="jd",
        source_id=str(jd.id),
        chunks=[{"index": i, "content": c} for i, c in enumerate(chunks)],
    )
    pipeline.trigger_embedding(source_type="jd", source_id=str(jd.id))

    return JDResponse(
        id=str(jd.id),
        filename=jd.filename,
        title=jd.title,
        company=jd.company,
        parse_status=jd.parse_status,
        structured=jd.structured,
        created_at=jd.created_at,
    )


@router.post("/upload", response_model=JDResponse, status_code=status.HTTP_201_CREATED)
async def upload_jd(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    parser = DocumentParser()
    raw_text = await parser.parse(content, file.filename or "jd")

    from app.core.config import get_settings
    from app.core.minio import get_minio
    import io

    cfg = get_settings()
    minio_client = get_minio()
    object_name = f"{tenant.id}/jds/{file.filename}"

    minio_client.put_object(
        bucket_name=cfg.minio_bucket,
        object_name=object_name,
        data=io.BytesIO(content),
        length=len(content),
        content_type=file.content_type or "application/octet-stream",
    )

    display_name = title or file.filename or "untitled"
    jd = JD(
        tenant_id=tenant.id,
        title=display_name,
        company=company,
        filename=display_name,
        file_url=object_name,
        raw_text=raw_text,
        parse_status="parsed",
    )
    db.add(jd)
    await db.flush()

    from app.services.document_parser import Chunker
    pipeline = EmbeddingPipeline(db)
    chunker = Chunker()
    chunks = chunker.chunk(raw_text, "jd")
    await pipeline.save_chunks(
        tenant_id=str(tenant.id),
        source_type="jd",
        source_id=str(jd.id),
        chunks=[{"index": i, "content": c} for i, c in enumerate(chunks)],
    )
    pipeline.trigger_embedding(source_type="jd", source_id=str(jd.id))

    return JDResponse(
        id=str(jd.id),
        filename=jd.filename,
        title=jd.title,
        company=jd.company,
        parse_status=jd.parse_status,
        structured=jd.structured,
        created_at=jd.created_at,
    )


@router.get("", response_model=List[JDResponse])
async def list_jds(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JD).where(JD.tenant_id == tenant.id).order_by(JD.created_at.desc())
    )
    jds = result.scalars().all()
    return [
        JDResponse(
            id=str(r.id),
            filename=r.filename,
            title=r.title,
            company=r.company,
            parse_status=r.parse_status,
            created_at=r.created_at,
        )
        for r in jds
    ]


@router.get("/{jd_id}", response_model=JDResponse)
async def get_jd(
    jd_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JD).where(JD.id == jd_id, JD.tenant_id == tenant.id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")
    return JDResponse(
        id=str(jd.id),
        filename=jd.filename,
        title=jd.title,
        company=jd.company,
        parse_status=jd.parse_status,
        created_at=jd.created_at,
    )


@router.get("/{jd_id}/analysis", response_model=JDAnalysisResponse)
async def analyze_jd(
    jd_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JD).where(JD.id == jd_id, JD.tenant_id == tenant.id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")

    agent = JDAgent(db=db)
    analysis = await agent.run(jd_id, str(tenant.id))

    return JDAnalysisResponse(jd_id=jd_id, analysis=analysis, parse_status=jd.parse_status)


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jd(
    jd_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JD).where(JD.id == jd_id, JD.tenant_id == tenant.id))
    jd = result.scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")
    # Nullify FK references in interviews before deleting
    from app.models.interview import Interview
    await db.execute(
        update(Interview)
        .where(Interview.jd_id == jd.id)
        .values(jd_id=None)
    )
    await db.delete(jd)
