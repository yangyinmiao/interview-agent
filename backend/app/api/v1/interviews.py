from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db, async_session_factory
from app.core.tenant import get_current_tenant
from app.models.tenant import Tenant
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.interview_report import InterviewReport
from app.schemas.interview import (
    BatchDeleteInterviews,
    InterviewCreate,
    InterviewResponse,
    AnswerRequest,
    QuestionResponse,
    InterviewMessageResponse,
    InterviewReportResponse,
    ReferenceAnswerResponse,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    data: InterviewCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    interview = Interview(
        tenant_id=tenant.id,
        resume_id=data.resume_id,
        jd_id=data.jd_id,
        question_bank_id=data.question_bank_id,
        mode=data.mode,
    )
    db.add(interview)
    await db.flush()

    return InterviewResponse(
        id=str(interview.id),
        mode=interview.mode,
        status=interview.status,
        resume_id=data.resume_id,
        jd_id=data.jd_id,
        question_bank_id=data.question_bank_id,
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
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
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
        ).limit(1)
    )
    first_msg = existing.scalar_one_or_none()
    if first_msg:
        return QuestionResponse(
            question=first_msg.content,
            round_count=1,
            max_rounds=10,
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
        "max_rounds": 10,
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

    result_state = await graph.ainvoke(initial_state)

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
        round_count=result_state.get("round_count", 1),
        max_rounds=10,
        status=interview.status,
    )


@router.post("/{interview_id}/respond", response_model=QuestionResponse)
async def respond_to_question(
    interview_id: str,
    data: AnswerRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Candidate answers, LangGraph evaluates and generates next question."""
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status != "active":
        raise HTTPException(status_code=400, detail="Interview is not active")

    # Save candidate's answer
    answer_msg = InterviewMessage(
        interview_id=interview.id,
        role="candidate",
        content=data.answer,
    )
    db.add(answer_msg)

    # Get current state from messages
    messages_result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.created_at.asc())
    )
    all_messages = messages_result.scalars().all()

    question_history = []
    last_question = ""
    for msg in all_messages:
        if msg.role == "interviewer":
            last_question = msg.content
        elif msg.role == "candidate" and last_question:
            question_history.append({"q": last_question, "a": msg.content})
            last_question = ""

    round_count = len(question_history)

    from app.graphs.interview_graph import build_interview_graph

    graph = build_interview_graph(db)

    state = {
        "tenant_id": str(tenant.id),
        "interview_id": interview_id,
        "resume_id": str(interview.resume_id) if interview.resume_id else "",
        "jd_id": str(interview.jd_id) if interview.jd_id else "",
        "question_bank_id": str(interview.question_bank_id) if interview.question_bank_id else "",
        "interview_mode": interview.mode or "basic",
        "max_rounds": 10,
        "resume_analysis": None,
        "jd_analysis": None,
        "retrieved_questions": [],
        "current_question": "",
        "current_answer": data.answer,
        "question_history": question_history,
        "follow_up_depth": 0,
        "round_count": round_count,
        "answer_evaluations": [],
        "final_report": None,
        "messages": [],
        "next_action": "evaluate",
    }

    result_state = await graph.ainvoke(state)

    next_action = result_state.get("next_action", "end")

    if next_action == "end":
        interview.status = "completed"
        interview.completed_at = None
        from datetime import datetime, timezone
        interview.completed_at = datetime.now(timezone.utc)

        # Save report
        report_data = result_state.get("final_report", {})
        report = InterviewReport(
            interview_id=interview.id,
            tenant_id=tenant.id,
            overall_score=report_data.get("overall_score"),
            scores=report_data.get("scores"),
            strengths=report_data.get("strengths", []),
            weaknesses=report_data.get("weaknesses", []),
            suggestions=report_data.get("suggestions", []),
            raw_analysis=str(report_data),
        )
        db.add(report)
        await db.flush()

        closing_msg = InterviewMessage(
            interview_id=interview.id,
            role="system",
            content="面试已结束，请查看评估报告。",
        )
        db.add(closing_msg)

        return QuestionResponse(
            question="面试结束",
            round_count=round_count,
            max_rounds=10,
            status="completed",
        )

    # Next question
    next_question = result_state.get("current_question", "")
    if next_question:
        question_msg = InterviewMessage(
            interview_id=interview.id,
            role="interviewer",
            content=next_question,
        )
        db.add(question_msg)

    return QuestionResponse(
        question=next_question or "请继续...",
        round_count=result_state.get("round_count", round_count + 1),
        max_rounds=10,
        status=interview.status,
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
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id, Interview.tenant_id == tenant.id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Get all messages to build question history for report generation
    messages_result = await db.execute(
        select(InterviewMessage)
        .where(InterviewMessage.interview_id == interview.id)
        .order_by(InterviewMessage.created_at.asc())
    )
    all_messages = messages_result.scalars().all()

    question_history = []
    last_question = ""
    for msg in all_messages:
        if msg.role == "interviewer":
            last_question = msg.content
        elif msg.role == "candidate" and last_question:
            question_history.append({"q": last_question, "a": msg.content})
            last_question = ""

    from app.graphs.interview_graph import build_interview_graph

    graph = build_interview_graph(db)

    state = {
        "tenant_id": str(tenant.id),
        "interview_id": interview_id,
        "resume_id": str(interview.resume_id) if interview.resume_id else "",
        "jd_id": str(interview.jd_id) if interview.jd_id else "",
        "question_bank_id": str(interview.question_bank_id) if interview.question_bank_id else "",
        "interview_mode": interview.mode or "basic",
        "max_rounds": 10,
        "resume_analysis": None,
        "jd_analysis": None,
        "retrieved_questions": [],
        "current_question": "",
        "current_answer": "",
        "question_history": question_history,
        "follow_up_depth": 0,
        "round_count": len(question_history),
        "answer_evaluations": [],
        "final_report": None,
        "messages": [],
        "next_action": "report",
    }

    result_state = await graph.ainvoke(state)

    # Save report
    report_data = result_state.get("final_report", {})
    report = InterviewReport(
        interview_id=interview.id,
        tenant_id=tenant.id,
        overall_score=report_data.get("overall_score"),
        scores=report_data.get("scores"),
        strengths=report_data.get("strengths", []),
        weaknesses=report_data.get("weaknesses", []),
        suggestions=report_data.get("suggestions", []),
        raw_analysis=str(report_data),
    )
    db.add(report)

    closing_msg = InterviewMessage(
        interview_id=interview.id,
        role="system",
        content="面试已结束，请查看评估报告。",
    )
    db.add(closing_msg)

    interview.status = "completed"
    from datetime import datetime, timezone
    interview.completed_at = datetime.now(timezone.utc)

    return {"status": "completed", "interview_id": interview_id}


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
        overall_score=float(report.overall_score) if report.overall_score else None,
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
            started_at=i.started_at,
            completed_at=i.completed_at,
        )
        for i in interviews
    ]
