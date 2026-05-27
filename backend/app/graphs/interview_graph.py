"""Interview LangGraph - orchestrates the complete interview flow."""

import json
import time
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.graphs.states import InterviewState
from app.agents.resume_agent import ResumeAgent
from app.agents.jd_agent import JDAgent
from app.agents.qbank_agent import QBankAgent
from app.agents.interviewer_agent import InterviewerAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.supervisor import SupervisorAgent
from app.core.qdrant import get_qdrant
from app.core.logging import get_structured_logger, set_interview_id, LogContext

logger = get_structured_logger("graphs.interview")


def build_interview_graph(db: AsyncSession) -> CompiledStateGraph:
    """Build the interview state graph with agent nodes."""

    resume_agent = ResumeAgent(db=db)
    jd_agent = JDAgent(db=db)
    qbank_agent = QBankAgent(qdrant=get_qdrant())
    interviewer_agent = InterviewerAgent()
    evaluator_agent = EvaluatorAgent()
    supervisor_agent = SupervisorAgent()

    workflow = StateGraph(InterviewState)

    # === Node Definitions ===

    async def prepare_context(state: InterviewState) -> InterviewState:
        """Prepare interview context by running ResumeAgent, JDAgent, QBankAgent sequentially."""
        tenant_id = state["tenant_id"]
        interview_id = state.get("interview_id", "")
        resume_id = state.get("resume_id", "")
        jd_id = state.get("jd_id", "")
        question_bank_id = state.get("question_bank_id", "")

        # Inject interview_id into log context
        if interview_id:
            set_interview_id(interview_id)

        logger.info(
            "Preparing interview context",
            interview_id=interview_id,
            has_resume=bool(resume_id),
            has_jd=bool(jd_id),
            has_qbank=bool(question_bank_id),
            mode=state.get("interview_mode", "basic"),
        )

        start = time.time()

        if resume_id:
            state["resume_analysis"] = await resume_agent.run(resume_id, tenant_id)
        else:
            state["resume_analysis"] = None

        if jd_id:
            state["jd_analysis"] = await jd_agent.run(jd_id, tenant_id)
        else:
            state["jd_analysis"] = None

        if question_bank_id:
            jd_context = state.get("jd_analysis", {})
            context_str = json.dumps(jd_context, ensure_ascii=False) if jd_context else ""
            state["retrieved_questions"] = await qbank_agent.search(question_bank_id, tenant_id, context=context_str)
        else:
            state["retrieved_questions"] = []

        logger.info(
            "Context prepared",
            duration_ms=round((time.time() - start) * 1000, 2),
            resume_ready=state["resume_analysis"] is not None,
            jd_ready=state["jd_analysis"] is not None,
            questions_retrieved=len(state.get("retrieved_questions", [])),
        )

        return state

    async def generate_question(state: InterviewState) -> InterviewState:
        """Generate the next interview question."""
        round_count = state.get("round_count", 0)
        start = time.time()

        result = await interviewer_agent.generate_question(
            mode=state.get("interview_mode", "basic"),
            resume_analysis=state.get("resume_analysis"),
            jd_analysis=state.get("jd_analysis"),
            retrieved_questions=state.get("retrieved_questions"),
            question_history=state.get("question_history", []),
            follow_up_depth=state.get("follow_up_depth", 0),
            round_count=round_count,
            max_rounds=state.get("max_rounds", 10),
            last_evaluation=state.get("answer_evaluations", [])[-1] if state.get("answer_evaluations") else None,
        )

        state["current_question"] = result.get("question", "")
        state["round_count"] = round_count + 1
        state["next_action"] = "wait"

        logger.info(
            f"Round {round_count + 1} question ready",
            question_length=len(result.get("question", "")),
            duration_ms=round((time.time() - start) * 1000, 2),
        )
        return state

    async def evaluate_answer(state: InterviewState) -> InterviewState:
        """Evaluate the candidate's answer."""
        start = time.time()

        evaluation = await evaluator_agent.evaluate_single(
            question=state.get("current_question", ""),
            answer=state.get("current_answer", ""),
        )

        question_entry = {
            "q": state.get("current_question", ""),
            "a": state.get("current_answer", ""),
            "evaluation": evaluation,
            "topic": evaluation.get("topic", "general"),
        }

        history = state.get("question_history", [])
        history.append(question_entry)
        state["question_history"] = history

        evals = state.get("answer_evaluations", [])
        evals.append(evaluation)
        state["answer_evaluations"] = evals

        logger.info(
            f"Answer evaluated, score={evaluation.get('score', '?')}",
            round_number=len(history),
            score=evaluation.get("score"),
            should_follow_up=evaluation.get("should_follow_up"),
            duration_ms=round((time.time() - start) * 1000, 2),
        )
        return state

    async def generate_report(state: InterviewState) -> InterviewState:
        """Generate the final interview report."""
        start = time.time()
        total_rounds = len(state.get("question_history", []))
        logger.info(f"Generating final report for {total_rounds} rounds")

        resume_summary = json.dumps(state.get("resume_analysis", {}), ensure_ascii=False)
        jd_summary = json.dumps(state.get("jd_analysis", {}), ensure_ascii=False)
        conversation = json.dumps(state.get("question_history", []), ensure_ascii=False, indent=2)
        evaluations = json.dumps(state.get("answer_evaluations", []), ensure_ascii=False, indent=2)

        report = await evaluator_agent.evaluate_overall(
            resume_summary=resume_summary,
            jd_summary=jd_summary,
            conversation_history=conversation,
            answer_evaluations=evaluations,
        )

        state["final_report"] = report
        logger.info(
            "Interview completed",
            total_rounds=total_rounds,
            overall_score=report.get("overall_score"),
            duration_ms=round((time.time() - start) * 1000, 2),
        )
        return state

    # === Router ===

    def router(state: InterviewState) -> Literal["ask", "end"]:
        decision = supervisor_agent.router(state)
        logger.debug(
            "Router decision",
            decision=decision,
            round_count=state.get("round_count", 0),
            max_rounds=state.get("max_rounds", 10),
            mode=state.get("interview_mode", "basic"),
        )
        return decision  # type: ignore

    # === Graph Construction ===

    workflow.add_node("prepare_context", prepare_context)
    workflow.add_node("generate_question", generate_question)
    workflow.add_node("evaluate_answer", evaluate_answer)
    workflow.add_node("generate_report", generate_report)

    # Conditional entry: start from prepare_context, evaluate_answer, or
    # generate_report based on state.next_action
    workflow.set_conditional_entry_point(
        lambda state: state.get("next_action", "prepare"),
        {
            "prepare": "prepare_context",
            "evaluate": "evaluate_answer",
            "report": "generate_report",
        },
    )

    workflow.add_edge("prepare_context", "generate_question")
    # After generating a question, always END — the next user answer triggers a
    # new graph run starting from evaluate_answer.
    workflow.add_edge("generate_question", END)

    workflow.add_conditional_edges(
        "evaluate_answer",
        router,
        {
            "ask": "generate_question",
            "end": "generate_report",
        },
    )

    workflow.add_edge("generate_report", END)

    return workflow.compile()
