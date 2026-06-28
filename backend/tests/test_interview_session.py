from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.supervisor import SupervisorAgent
from app.interview.session import InterviewSession
from app.models.interview_message import InterviewMessage


def scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def messages_result(messages):
    result = MagicMock()
    result.scalars.return_value.all.return_value = messages
    return result


def make_interview(max_rounds=10):
    return SimpleNamespace(
        id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
        tenant_id="f64ac857-8ee0-487a-a527-7399aff8ad93",
        mode="basic",
        max_rounds=max_rounds,
        status="active",
        follow_up_depth=0,
        context_cache={},
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_answer_persists_evaluation_and_counts_completed_round_once():
    db = AsyncMock()
    db.add = MagicMock()
    interview = make_interview()
    question = InterviewMessage(role="interviewer", content="What is idempotency?")
    question.id = "question-1"
    db.execute.side_effect = [scalar_result(interview), messages_result([question])]

    evaluator = MagicMock()
    evaluator.evaluate_single = AsyncMock(
        return_value={
            "score": 8,
            "topic": "distributed systems",
            "brief_feedback": "clear",
            "should_follow_up": False,
        }
    )
    interviewer = MagicMock()
    interviewer.generate_question = AsyncMock(return_value={"question": "Next question"})

    result = await InterviewSession(
        db,
        evaluator=evaluator,
        interviewer=interviewer,
        supervisor=SupervisorAgent(),
    ).answer(
        interview_id=str(interview.id),
        tenant_id=str(interview.tenant_id),
        answer="Use a stable request key.",
    )

    assert result.round_count == 1
    assert result.completed is False
    added_messages = [call.args[0] for call in db.add.call_args_list]
    candidate = next(message for message in added_messages if message.role == "candidate")
    assert candidate.meta_data["evaluation"]["score"] == 8
    assert sum(message.role == "candidate" for message in added_messages) == 1
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_last_round_uses_all_persisted_evaluations_for_report():
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    interview = make_interview(max_rounds=2)

    first_question = InterviewMessage(role="interviewer", content="Q1")
    first_question.id = "q1"
    first_answer = InterviewMessage(
        role="candidate",
        content="A1",
        meta_data={"evaluation": {"score": 6, "topic": "python"}},
    )
    second_question = InterviewMessage(role="interviewer", content="Q2")
    second_question.id = "q2"
    db.execute.side_effect = [
        scalar_result(interview),
        messages_result([first_question, first_answer, second_question]),
    ]

    evaluator = MagicMock()
    evaluator.evaluate_single = AsyncMock(
        return_value={"score": 9, "topic": "database", "should_follow_up": False}
    )
    evaluator.evaluate_overall = AsyncMock(
        return_value={
            "overall_score": 7.5,
            "scores": {},
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
        }
    )

    result = await InterviewSession(db, evaluator=evaluator).answer(
        interview_id=str(interview.id),
        tenant_id=str(interview.tenant_id),
        answer="A2",
    )

    assert result.completed is True
    assert result.round_count == 2
    report_args = evaluator.evaluate_overall.await_args.kwargs
    assert '"score": 6' in report_args["answer_evaluations"]
    assert '"score": 9' in report_args["answer_evaluations"]
    assert interview.status == "completed"
