from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.question_bank import QuestionBank
from app.schemas.question_bank import QuestionBankCreate, QuestionBankResponse, QuestionCreate, QuestionResponse
from app.services.embedding_pipeline import EmbeddingPipeline

router = APIRouter(prefix="/question-banks", tags=["question_banks"])


@router.post("/upload", response_model=QuestionBankResponse, status_code=status.HTTP_201_CREATED)
async def upload_question_bank(
    file: UploadFile = File(...),
    name: str = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    from app.services.document_parser import DocumentParser, Chunker

    parser = DocumentParser()
    raw_text = await parser.parse(content, file.filename or "questions")

    qb = QuestionBank(
        tenant_id=tenant.id,
        name=name or file.filename or "Untitled Bank",
        description=f"Uploaded from {file.filename}",
    )
    db.add(qb)
    await db.flush()

    chunker = Chunker()
    chunks = chunker.chunk(raw_text, "question_bank")
    pipeline = EmbeddingPipeline(db)
    await pipeline.save_chunks(
        tenant_id=str(tenant.id),
        source_type="question_bank",
        source_id=str(qb.id),
        chunks=[{"index": i, "content": c} for i, c in enumerate(chunks)],
    )
    pipeline.trigger_embedding(source_type="question_bank", source_id=str(qb.id))

    return QuestionBankResponse(id=str(qb.id), name=qb.name, description=qb.description, created_at=qb.created_at)


@router.get("", response_model=List[QuestionBankResponse])
async def list_question_banks(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.tenant_id == tenant.id).order_by(QuestionBank.created_at.desc())
    )
    banks = result.scalars().all()
    return [
        QuestionBankResponse(id=str(b.id), name=b.name, description=b.description, created_at=b.created_at)
        for b in banks
    ]


@router.get("/{bank_id}", response_model=QuestionBankResponse)
async def get_question_bank(
    bank_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == bank_id, QuestionBank.tenant_id == tenant.id)
    )
    qb = result.scalar_one_or_none()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return QuestionBankResponse(id=str(qb.id), name=qb.name, description=qb.description, created_at=qb.created_at)


@router.delete("/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_bank(
    bank_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == bank_id, QuestionBank.tenant_id == tenant.id)
    )
    qb = result.scalar_one_or_none()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    await db.delete(qb)
