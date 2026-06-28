from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.question_bank import QuestionBank
from app.schemas.question_bank import QuestionBankResponse
from app.services.embedding_pipeline import EmbeddingPipeline

router = APIRouter(prefix="/question-banks", tags=["question_banks"])


async def _process_files(
    files: List[UploadFile],
    bank_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> int:
    """Process and chunk files into an existing question bank. Returns total chunk count."""
    from app.services.document_parser import DocumentParser, Chunker

    parser = DocumentParser()
    chunker = Chunker()
    pipeline = EmbeddingPipeline(db)
    all_texts: List[str] = []

    for file in files:
        content = await file.read()
        raw_text = await parser.parse(content, file.filename or "questions")
        all_texts.append(raw_text)

    combined = "\n\n".join(all_texts)
    chunks = chunker.chunk(combined, "question_bank")
    await pipeline.save_chunks(
        tenant_id=tenant_id,
        source_type="question_bank",
        source_id=bank_id,
        chunks=[{"index": i, "content": c} for i, c in enumerate(chunks)],
    )
    pipeline.trigger_embedding(source_type="question_bank", source_id=bank_id)
    return len(chunks)


@router.post("", response_model=QuestionBankResponse, status_code=status.HTTP_201_CREATED)
async def create_question_bank(
    name: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Create a question bank with a name and optional initial files."""
    qb = QuestionBank(
        tenant_id=tenant.id,
        name=name,
        description="",
    )
    db.add(qb)
    await db.flush()

    filenames: List[str] = []
    if files:
        filenames = [f.filename or "unknown" for f in files]
        await _process_files(files, str(qb.id), str(tenant.id), db)

    qb.description = ", ".join(filenames) if filenames else ""
    await db.flush()

    return QuestionBankResponse(
        id=str(qb.id), name=qb.name, description=qb.description, created_at=qb.created_at
    )


@router.post("/{bank_id}/add-files", response_model=QuestionBankResponse)
async def add_files_to_bank(
    bank_id: str,
    files: List[UploadFile] = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Add more files to an existing question bank."""
    result = await db.execute(
        select(QuestionBank).where(
            QuestionBank.id == bank_id, QuestionBank.tenant_id == tenant.id
        )
    )
    qb = result.scalar_one_or_none()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")

    new_filenames = [f.filename or "unknown" for f in files]
    existing = qb.description or ""
    all_filenames = ([existing] if existing else []) + new_filenames
    qb.description = ", ".join(all_filenames)

    await _process_files(files, str(qb.id), str(tenant.id), db)

    return QuestionBankResponse(
        id=str(qb.id), name=qb.name, description=qb.description, created_at=qb.created_at
    )


@router.get("", response_model=List[QuestionBankResponse])
async def list_question_banks(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank)
        .where(QuestionBank.tenant_id == tenant.id)
        .order_by(QuestionBank.created_at.desc())
    )
    banks = result.scalars().all()
    return [
        QuestionBankResponse(
            id=str(b.id), name=b.name, description=b.description, created_at=b.created_at
        )
        for b in banks
    ]


@router.get("/{bank_id}", response_model=QuestionBankResponse)
async def get_question_bank(
    bank_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank).where(
            QuestionBank.id == bank_id, QuestionBank.tenant_id == tenant.id
        )
    )
    qb = result.scalar_one_or_none()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return QuestionBankResponse(
        id=str(qb.id), name=qb.name, description=qb.description, created_at=qb.created_at
    )


@router.delete("/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_bank(
    bank_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionBank).where(
            QuestionBank.id == bank_id, QuestionBank.tenant_id == tenant.id
        )
    )
    qb = result.scalar_one_or_none()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    # Nullify FK references in interviews before deleting
    from app.models.interview import Interview
    await db.execute(
        update(Interview)
        .where(Interview.question_bank_id == qb.id, Interview.tenant_id == tenant.id)
        .values(question_bank_id=None)
    )
    from app.materials.lifecycle import PreparationMaterialLifecycle
    await PreparationMaterialLifecycle(db).delete(
        tenant_id=str(tenant.id),
        source_type="question_bank",
        source_id=str(qb.id),
    )
    await db.delete(qb)
