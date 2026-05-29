from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeAnalysisResponse
from app.services.document_parser import DocumentParser
from app.services.embedding_pipeline import EmbeddingPipeline
from app.agents.resume_agent import ResumeAgent

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    content = await file.read()
    parser = DocumentParser()
    raw_text = await parser.parse(content, file.filename or "resume")

    from app.core.minio import get_minio, get_settings

    settings = get_minio.__module__
    from app.core.config import get_settings as _gs
    cfg = _gs()
    from app.core.minio import get_minio as _gm
    minio_client = _gm()
    object_name = f"{tenant.id}/resumes/{file.filename}"

    import io
    minio_client.put_object(
        bucket_name=cfg.minio_bucket,
        object_name=object_name,
        data=io.BytesIO(content),
        length=len(content),
        content_type=file.content_type or "application/octet-stream",
    )

    resume = Resume(
        tenant_id=tenant.id,
        filename=file.filename or "untitled",
        file_url=object_name,
        raw_text=raw_text,
        parse_status="parsed",
    )
    db.add(resume)
    await db.flush()

    # Save chunks and trigger async embedding
    pipeline = EmbeddingPipeline(db)
    from app.services.document_parser import Chunker
    chunker = Chunker()
    chunks = chunker.chunk(raw_text, "resume")
    await pipeline.save_chunks(
        tenant_id=str(tenant.id),
        source_type="resume",
        source_id=str(resume.id),
        chunks=[{"index": i, "content": c} for i, c in enumerate(chunks)],
    )
    pipeline.trigger_embedding(source_type="resume", source_id=str(resume.id))

    return ResumeResponse(
        id=str(resume.id),
        filename=resume.filename,
        parse_status=resume.parse_status,
        structured=resume.structured,
        created_at=resume.created_at,
    )


@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.tenant_id == tenant.id).order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    return [
        ResumeResponse(
            id=str(r.id),
            filename=r.filename,
            parse_status=r.parse_status,
            structured=r.structured,
            created_at=r.created_at,
        )
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.tenant_id == tenant.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeResponse(
        id=str(resume.id),
        filename=resume.filename,
        parse_status=resume.parse_status,
        structured=resume.structured,
        created_at=resume.created_at,
    )


@router.get("/{resume_id}/analysis", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.tenant_id == tenant.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    agent = ResumeAgent(db=db)
    analysis = await agent.run(resume_id, str(tenant.id))

    return ResumeAnalysisResponse(
        resume_id=resume_id,
        analysis=analysis,
        parse_status=resume.parse_status,
    )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.tenant_id == tenant.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    # Nullify FK references in interviews before deleting
    from app.models.interview import Interview
    await db.execute(
        update(Interview)
        .where(Interview.resume_id == resume.id)
        .values(resume_id=None)
    )
    await db.delete(resume)
