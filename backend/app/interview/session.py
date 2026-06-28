"""The deep module that owns one completed interview round.

HTTP and SSE are adapters at the event-delivery seam. Both cross this module's
same interface, so evaluation, routing, persistence, and round counting cannot
drift apart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.interviewer_agent import InterviewerAgent
from app.agents.supervisor import SupervisorAgent
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.interview_report import InterviewReport


EventSink = Callable[[dict], Awaitable[None]]


class InterviewSessionError(Exception):
    """Base error exposed by the Practice Interview interface."""


class InterviewNotFoundError(InterviewSessionError):
    pass


class InterviewNotActiveError(InterviewSessionError):
    pass


class DuplicateAnswerError(InterviewSessionError):
    pass


class InterviewNotStartedError(InterviewSessionError):
    pass


@dataclass(frozen=True)
class InterviewTurnResult:
    question: str
    evaluation: dict
    round_count: int
    max_rounds: int
    status: str
    completed: bool


class InterviewSession:
    """Complete and persist one Interview Round through a single interface."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        evaluator: Optional[EvaluatorAgent] = None,
        interviewer: Optional[InterviewerAgent] = None,
        supervisor: Optional[SupervisorAgent] = None,
    ):
        self.db = db
        self.evaluator = evaluator or EvaluatorAgent()
        self.interviewer = interviewer or InterviewerAgent()
        self.supervisor = supervisor or SupervisorAgent()

    async def answer(
        self,
        *,
        interview_id: str,
        tenant_id: str,
        answer: str,
        request_id: Optional[str] = None,
        event_sink: Optional[EventSink] = None,
    ) -> InterviewTurnResult:
        interview = await self._load_interview(interview_id, tenant_id)

        if request_id:
            duplicate = await self.db.execute(
                select(InterviewMessage.id).where(
                    InterviewMessage.interview_id == interview.id,
                    InterviewMessage.request_id == request_id,
                )
            )
            if duplicate.scalar_one_or_none():
                raise DuplicateAnswerError("This answer request was already processed")

        messages = await self._load_messages(interview)
        current_question = next(
            (message for message in reversed(messages) if message.role == "interviewer"),
            None,
        )
        if current_question is None:
            raise InterviewNotStartedError("Interview has not started")

        history, evaluations = self._completed_history(messages)
        evaluation = await self.evaluator.evaluate_single(
            question=current_question.content,
            answer=answer,
        )
        current_round = len(history) + 1

        candidate_message = InterviewMessage(
            interview_id=interview.id,
            role="candidate",
            content=answer,
            request_id=request_id,
            meta_data={
                "question_id": str(current_question.id),
                "evaluation": evaluation,
            },
        )
        self.db.add(candidate_message)

        round_entry = {
            "q": current_question.content,
            "a": answer,
            "evaluation": evaluation,
            "topic": evaluation.get("topic", "general"),
        }
        history.append(round_entry)
        evaluations.append(evaluation)

        if event_sink:
            await event_sink(
                {
                    "type": "evaluated",
                    "score": evaluation.get("score"),
                    "feedback": evaluation.get("brief_feedback", ""),
                }
            )

        router_state = {
            "round_count": current_round,
            "max_rounds": interview.max_rounds,
            "interview_mode": interview.mode,
            "follow_up_depth": interview.follow_up_depth or 0,
            "answer_evaluations": [evaluation],
        }
        if self.supervisor.router(router_state) == "end":
            closing = await self._complete(interview, history, evaluations)
            await self.db.commit()
            return InterviewTurnResult(
                question=closing,
                evaluation=evaluation,
                round_count=current_round,
                max_rounds=interview.max_rounds,
                status="completed",
                completed=True,
            )

        self._advance_follow_up_depth(interview, evaluation)
        question = await self._next_question(
            interview=interview,
            history=history,
            evaluations=evaluations,
            current_round=current_round,
            event_sink=event_sink,
        )
        self.db.add(
            InterviewMessage(
                interview_id=interview.id,
                role="interviewer",
                content=question,
                meta_data={"topic": "general"},
            )
        )
        await self.db.commit()
        return InterviewTurnResult(
            question=question,
            evaluation=evaluation,
            round_count=current_round,
            max_rounds=interview.max_rounds,
            status="active",
            completed=False,
        )

    async def finish(self, *, interview_id: str, tenant_id: str) -> str:
        """Finish an active Practice Interview using every persisted round."""
        interview = await self._load_interview(interview_id, tenant_id)
        messages = await self._load_messages(interview)
        history, evaluations = self._completed_history(messages)
        closing = await self._complete(interview, history, evaluations)
        await self.db.commit()
        return closing

    async def _load_interview(self, interview_id: str, tenant_id: str) -> Interview:
        result = await self.db.execute(
            select(Interview)
            .where(Interview.id == interview_id, Interview.tenant_id == tenant_id)
            .with_for_update()
        )
        interview = result.scalar_one_or_none()
        if interview is None:
            raise InterviewNotFoundError("Interview not found")
        if interview.status != "active":
            raise InterviewNotActiveError("Interview is not active")
        return interview

    async def _load_messages(self, interview: Interview) -> list[InterviewMessage]:
        result = await self.db.execute(
            select(InterviewMessage)
            .where(InterviewMessage.interview_id == interview.id)
            .order_by(InterviewMessage.created_at.asc(), InterviewMessage.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _completed_history(messages: list[InterviewMessage]) -> tuple[list[dict], list[dict]]:
        history: list[dict] = []
        evaluations: list[dict] = []
        pending_question: Optional[InterviewMessage] = None

        for message in messages:
            if message.role == "interviewer":
                pending_question = message
            elif message.role == "candidate" and pending_question is not None:
                evaluation = (message.meta_data or {}).get("evaluation")
                entry = {
                    "q": pending_question.content,
                    "a": message.content,
                    "topic": (evaluation or {}).get(
                        "topic", (pending_question.meta_data or {}).get("topic", "general")
                    ),
                }
                if evaluation:
                    entry["evaluation"] = evaluation
                    evaluations.append(evaluation)
                history.append(entry)
                pending_question = None

        return history, evaluations

    @staticmethod
    def _advance_follow_up_depth(interview: Interview, evaluation: dict) -> None:
        should_follow_up = bool(evaluation.get("should_follow_up"))
        limit = 3 if interview.mode == "follow_up" else 2
        if interview.mode in {"follow_up", "deep"} and should_follow_up:
            interview.follow_up_depth = min((interview.follow_up_depth or 0) + 1, limit)
        else:
            interview.follow_up_depth = 0

    async def _next_question(
        self,
        *,
        interview: Interview,
        history: list[dict],
        evaluations: list[dict],
        current_round: int,
        event_sink: Optional[EventSink],
    ) -> str:
        context = interview.context_cache or {}
        kwargs = {
            "mode": interview.mode or "basic",
            "resume_analysis": context.get("resume_analysis"),
            "jd_analysis": context.get("jd_analysis"),
            "retrieved_questions": context.get("retrieved_questions", []),
            "question_history": history,
            "follow_up_depth": interview.follow_up_depth or 0,
            "round_count": current_round,
            "max_rounds": interview.max_rounds,
            "last_evaluation": evaluations[-1] if evaluations else None,
        }

        if event_sink:
            chunks: list[str] = []
            async for token in self.interviewer.astream_question(**kwargs):
                chunks.append(token)
                await event_sink({"type": "token", "content": token})
            return "".join(chunks).strip()

        result = await self.interviewer.generate_question(**kwargs)
        return result.get("question", "").strip()

    async def _complete(
        self,
        interview: Interview,
        history: list[dict],
        evaluations: list[dict],
    ) -> str:
        context = interview.context_cache or {}
        report_data = await self.evaluator.evaluate_overall(
            resume_summary=json.dumps(context.get("resume_analysis", {}), ensure_ascii=False),
            jd_summary=json.dumps(context.get("jd_analysis", {}), ensure_ascii=False),
            conversation_history=json.dumps(history, ensure_ascii=False, indent=2),
            answer_evaluations=json.dumps(evaluations, ensure_ascii=False, indent=2),
        )
        self.db.add(
            InterviewReport(
                interview_id=interview.id,
                tenant_id=interview.tenant_id,
                overall_score=report_data.get("overall_score"),
                scores=report_data.get("scores"),
                strengths=report_data.get("strengths", []),
                weaknesses=report_data.get("weaknesses", []),
                suggestions=report_data.get("suggestions", []),
                raw_analysis=json.dumps(report_data, ensure_ascii=False),
            )
        )
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        closing = self._closing_message(report_data.get("overall_score"))
        self.db.add_all(
            [
                InterviewMessage(
                    interview_id=interview.id,
                    role="interviewer",
                    content=closing,
                    meta_data={"kind": "closing"},
                ),
                InterviewMessage(
                    interview_id=interview.id,
                    role="system",
                    content="面试已结束，请查看评估报告。",
                ),
            ]
        )
        return closing

    @staticmethod
    def _closing_message(overall_score: Optional[float]) -> str:
        if overall_score is not None and overall_score >= 8:
            return f"感谢您参加本次面试！本次综合得分为 {overall_score} 分，整体表现出色。"
        if overall_score is not None and overall_score >= 6:
            return f"感谢您参加本次面试！本次综合得分为 {overall_score} 分，整体表现不错。"
        return "感谢您参加本次面试！评估已经完成，请查看报告中的改进建议。"
