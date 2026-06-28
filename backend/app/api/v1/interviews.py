from typing import List
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.core.database import get_db, async_session_factory
from app.core.tenant import get_current_tenant
from app.services.llm_factory import get_langfuse_handler
from app.models.tenant import Tenant
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.interview_report import InterviewReport
from app.interview.session import (
    DuplicateAnswerError,
    InterviewNotActiveError,
    InterviewNotFoundError,
    InterviewNotStartedError,
    InterviewSession,
)
from app.schemas.interview import (
    BatchDeleteInterviews,
    InterviewCreate,
    InterviewResponse,
    AnswerRequest,
    QuestionResponse,
    InterviewMessageResponse,
    InterviewReportResponse,
    ReferenceAnswerResponse,
    ProgressTrendResponse,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    data: InterviewCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    from app.models.jd import JD
    from app.models.question_bank import QuestionBank
    from app.models.resume import Resume

    selected_materials = (
        (Resume, data.resume_id, "Resume"),
        (JD, data.jd_id, "JD"),
        (QuestionBank, data.question_bank_id, "Question bank"),
    )
    for model, material_id, label in selected_materials:
        if material_id is None:
            continue
        owned = await db.execute(
            select(model.id).where(model.id == material_id, model.tenant_id == tenant.id)
        )
        if owned.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail=f"{label} not found")

    interview = Interview(
        tenant_id=tenant.id,
        resume_id=data.resume_id,
        jd_id=data.jd_id,
        question_bank_id=data.question_bank_id,
        mode=data.mode,
        max_rounds=data.max_rounds,
    )
    db.add(interview)
    await db.flush()

    return InterviewResponse(
        id=str(interview.id),
        mode=interview.mode,
        status=interview.status,
        resume_id=str(data.resume_id) if data.resume_id else None,
        jd_id=str(data.jd_id) if data.jd_id else None,
        question_bank_id=str(data.question_bank_id) if data.question_bank_id else None,
        max_rounds=interview.max_rounds,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
    )


@router.get("", response_model=List[InterviewResponse])
async def list_interviews(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Interview).where(Interview.tenant_id == tenant.id).order_by(Interview.created_at.desc())
    )
    interviews = result.scalars().all()
    return [
        InterviewResponse(
            id=str(i.id),
            mode=i.mode,
            status=i.status,
            resume_id=str(i.resume_id) if i.resume_id else None,
            jd_id=str(i.jd_id) if i.jd_id else None,
            question_bank_id=str(i.question_bank_id) if i.question_bank_id else None,
            max_rounds=i.max_rounds,
            started_at=i.started_at,
            completed_at=i.completed_at,
        )
        for i in interviews
    ]


@router.get("/progress", response_model=ProgressTrendResponse)
async def get_progress_trend(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Compare completed Practice Interviews and persisted Answer Evaluations."""
    from app.interview.progress import build_progress_trend

    result = await db.execute(
        select(InterviewReport, Interview)
        .join(Interview, Interview.id == InterviewReport.interview_id)
        .where(InterviewReport.tenant_id == tenant.id)
        .order_by(Interview.completed_at.asc(), Interview.id.asc())
    )
    report_rows = [
        {
            "interview_id": str(interview.id),
            "completed_at": interview.completed_at or report.created_at,
            "overall_score": report.overall_score,
            "scores": report.scores or {},
        }
        for report, interview in result.all()
    ]

    interview_ids = [row["interview_id"] for row in report_rows]
    evaluation_rows: list[dict] = []
    if interview_ids:
        messages = await db.execute(
            select(InterviewMessage)
            .join(Interview, Interview.id == InterviewMessage.interview_id)
            .where(
                Interview.tenant_id == tenant.id,
                InterviewMessage.interview_id.in_(interview_ids),
                InterviewMessage.role == "candidate",
            )
            .order_by(Interview.completed_at.asc(), InterviewMessage.created_at.asc())
        )
        evaluation_rows = [
            evaluation
            for message in messages.scalars().all()
            if (evaluation := (message.meta_data or {}).get("evaluation"))
        ]

    return build_progress_trend(report_rows, evaluation_rows)


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return InterviewResponse(
        id=str(interview.id),
        mode=interview.mode,
        status=interview.status,
        resume_id=str(interview.resume_id) if interview.resume_id else None,
        jd_id=str(interview.jd_id) if interview.jd_id else None,
        question_bank_id=str(interview.question_bank_id) if interview.question_bank_id else None,
        max_rounds=interview.max_rounds,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
    )


@router.post("/{interview_id}/start", response_model=QuestionResponse)
async def start_interview(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Start the interview: run LangGraph to generate the first question."""
    result = await db.execute(
        select(Interview)
        .where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
        .with_for_update()
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status != "active":
        raise HTTPException(status_code=400, detail="Interview is not active")

    # Guard: if already started, return the existing first question
    existing = await db.execute(
        select(InterviewMessage).where(
            InterviewMessage.interview_id == interview.id,
            InterviewMessage.role == "interviewer",
        ).order_by(InterviewMessage.created_at.asc(), InterviewMessage.id.asc()).limit(1)
    )
    first_msg = existing.scalar_one_or_none()
    if first_msg:
        completed_rounds = await db.scalar(
            select(func.count(InterviewMessage.id)).where(
                InterviewMessage.interview_id == interview.id,
                InterviewMessage.role == "candidate",
            )
        )
        return QuestionResponse(
            question=first_msg.content,
            round_count=completed_rounds or 0,
            max_rounds=interview.max_rounds,
            status=interview.status,
        )

    from app.graphs.interview_graph import build_interview_graph

    graph = build_interview_graph(db)

    initial_state = {
        "tenant_id": str(tenant.id),
        "interview_id": interview_id,
        "resume_id": str(interview.resume_id) if interview.resume_id else "",
        "jd_id": str(interview.jd_id) if interview.jd_id else "",
        "question_bank_id": str(interview.question_bank_id) if interview.question_bank_id else "",
        "interview_mode": interview.mode or "basic",
        "max_rounds": interview.max_rounds,
        "resume_analysis": None,
        "jd_analysis": None,
        "retrieved_questions": [],
        "current_question": None,
        "current_answer": None,
        "question_history": [],
        "follow_up_depth": 0,
        "round_count": 0,
        "answer_evaluations": [],
        "final_report": None,
        "messages": [],
        "next_action": "prepare",
    }

    try:
        result_state = await graph.ainvoke(
            initial_state,
            config={"callbacks": [get_langfuse_handler(session_id=interview_id)]},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    # Persist context so subsequent requests don't need to re-analyse
    interview.context_cache = {
        "resume_analysis": result_state.get("resume_analysis"),
        "jd_analysis": result_state.get("jd_analysis"),
        "retrieved_questions": result_state.get("retrieved_questions", []),
    }
    interview.follow_up_depth = 0

    # Save the first question as a message
    question = result_state.get("current_question", "欢迎参加面试，请先简单介绍一下自己。")
    if not question:
        question = "欢迎参加面试，请先简单介绍一下自己。"

    msg = InterviewMessage(
        interview_id=interview.id,
        role="interviewer",
        content=question,
    )
    db.add(msg)
    await db.flush()

    return QuestionResponse(
        question=question,
        round_count=0,
        max_rounds=interview.max_rounds,
        status=interview.status,
    )


@router.post("/{interview_id}/respond", response_model=QuestionResponse)
async def respond_to_question(
    interview_id: str,
    data: AnswerRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Complete one Interview Round through the shared JSON adapter."""
    try:
        result = await InterviewSession(db).answer(
            interview_id=interview_id,
            tenant_id=str(tenant.id),
            answer=data.answer,
            request_id=data.request_id,
        )
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InterviewNotActiveError, InterviewNotStartedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DuplicateAnswerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return QuestionResponse(
        question=result.question,
        round_count=result.round_count,
        max_rounds=result.max_rounds,
        status=result.status,
    )


@router.post("/{interview_id}/respond-stream")
async def respond_stream(
    interview_id: str,
    data: AnswerRequest,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Complete one Interview Round through the shared SSE adapter."""

    async def safe_generate():
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        queue: asyncio.Queue[dict] = asyncio.Queue()
        task: asyncio.Task | None = None

        async def emit(event: dict) -> None:
            await queue.put(event)

        try:
            async with async_session_factory() as db:
                task = asyncio.create_task(
                    InterviewSession(db).answer(
                        interview_id=interview_id,
                        tenant_id=str(tenant.id),
                        answer=data.answer,
                        request_id=data.request_id,
                        event_sink=emit,
                    )
                )
                while not task.done() or not queue.empty():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                result = await task
                done = {
                    "type": "done",
                    "content": result.question,
                    "round_count": result.round_count,
                    "max_rounds": result.max_rounds,
                    "completed": result.completed,
                }
                yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
        except InterviewNotFoundError as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        except (InterviewNotActiveError, InterviewNotStartedError, DuplicateAnswerError) as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(
        safe_generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{interview_id}/messages", response_model=List[InterviewMessageResponse])
async def get_messages(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    msgs = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.created_at.asc())
    )
    return [
        InterviewMessageResponse(
            id=str(m.id), role=m.role, content=m.content, metadata=m.meta_data, created_at=m.created_at
        )
        for m in msgs.scalars().all()
    ]


@router.post("/{interview_id}/messages/{message_id}/reference-answer", response_model=ReferenceAnswerResponse)
async def get_reference_answer(
    interview_id: str,
    message_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate (or retrieve cached) reference answer for an interviewer question."""
    # Verify interview belongs to tenant
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Get the message
    result = await db.execute(
        select(InterviewMessage).where(
            InterviewMessage.id == message_id,
            InterviewMessage.interview_id == interview.id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.role != "interviewer":
        raise HTTPException(status_code=400, detail="Reference answer only available for interviewer messages")

    # Check if already cached
    if msg.meta_data and msg.meta_data.get("reference_answer"):
        return ReferenceAnswerResponse(
            message_id=str(msg.id),
            reference_answer=msg.meta_data["reference_answer"],
            cached=True,
        )

    # Generate reference answer
    from app.agents.interviewer_agent import InterviewerAgent

    agent = InterviewerAgent()
    reference_answer = await agent.generate_reference_answer(question=msg.content)

    # Save to message metadata
    msg.meta_data = {**(msg.meta_data or {}), "reference_answer": reference_answer}
    await db.flush()

    return ReferenceAnswerResponse(
        message_id=str(msg.id),
        reference_answer=reference_answer,
        cached=False,
    )


@router.post("/{interview_id}/end", response_model=dict)
async def end_interview(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    try:
        closing = await InterviewSession(db).finish(
            interview_id=interview_id,
            tenant_id=str(tenant.id),
        )
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InterviewNotActiveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "completed", "interview_id": interview_id, "closing": closing}


@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
async def get_report(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewReport).where(
            InterviewReport.interview_id == interview_id,
            InterviewReport.tenant_id == tenant.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return InterviewReportResponse(
        id=str(report.id),
        interview_id=str(report.interview_id),
        overall_score=float(report.overall_score) if report.overall_score is not None else None,
        scores=report.scores,
        strengths=report.strengths,
        weaknesses=report.weaknesses,
        suggestions=report.suggestions,
        raw_analysis=report.raw_analysis,
        created_at=report.created_at,
    )


@router.delete("/batch", response_model=dict)
async def batch_delete_interviews(
    data: BatchDeleteInterviews,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Batch delete interviews and their related data (messages, reports)."""
    # First, find which interview IDs actually belong to this tenant
    tenant_result = await db.execute(
        select(Interview.id).where(
            Interview.id.in_(data.ids),
            Interview.tenant_id == tenant.id,
        )
    )
    tenant_ids = [row[0] for row in tenant_result.fetchall()]

    if not tenant_ids:
        return {"deleted": 0}

    # Delete messages (no tenant_id column on InterviewMessage)
    await db.execute(
        delete(InterviewMessage).where(
            InterviewMessage.interview_id.in_(tenant_ids)
        )
    )

    # Delete reports
    await db.execute(
        delete(InterviewReport).where(
            InterviewReport.interview_id.in_(tenant_ids),
            InterviewReport.tenant_id == tenant.id,
        )
    )

    # Delete interviews
    result = await db.execute(
        delete(Interview).where(
            Interview.id.in_(tenant_ids),
        )
    )

    return {"deleted": result.rowcount}


@router.delete("/{interview_id}", response_model=dict)
async def delete_interview(
    interview_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single interview and its related data (messages, reports)."""
    result = await db.execute(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.tenant_id == tenant.id,
        )
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Delete messages (no tenant_id column)
    await db.execute(
        delete(InterviewMessage).where(
            InterviewMessage.interview_id == interview.id
        )
    )

    # Delete report
    await db.execute(
        delete(InterviewReport).where(
            InterviewReport.interview_id == interview.id,
            InterviewReport.tenant_id == tenant.id,
        )
    )

    # Delete interview
    await db.execute(
        delete(Interview).where(Interview.id == interview.id)
    )

    return {"deleted": interview_id}
