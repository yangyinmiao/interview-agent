"""Evaluator agent for assessing interview answers and generating reports."""

import json
from typing import Optional
from app.agents.base import BaseAgent
from app.prompts.evaluation import ANSWER_EVALUATION_PROMPT, FINAL_REPORT_PROMPT
from app.services.llm_factory import get_llm_small
from app.core.logging import get_structured_logger

logger = get_structured_logger("agents.evaluator")


class EvaluatorAgent(BaseAgent):
    """Agent responsible for evaluating answers and generating interview reports."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._small_llm = None

    @property
    def small_llm(self):
        if self._small_llm is None:
            self._small_llm = get_llm_small()
        return self._small_llm

    async def evaluate_single(self, question: str, answer: str) -> dict:
        """Evaluate a single interview answer."""
        prompt = ANSWER_EVALUATION_PROMPT.format(question=question, answer=answer)
        response = await self.small_llm.ainvoke(prompt)
        try:
            result = json.loads(response.content)
            logger.debug(
                "Answer evaluated",
                score=result.get("score"),
                should_follow_up=result.get("should_follow_up"),
            )
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse evaluation JSON")
            return {"score": 5, "brief_feedback": "无法解析评估结果", "should_follow_up": False}

    async def evaluate_overall(
        self,
        resume_summary: str,
        jd_summary: str,
        conversation_history: str,
        answer_evaluations: str,
    ) -> dict:
        """Generate a comprehensive final interview report."""
        logger.info("Generating final interview report")
        prompt = FINAL_REPORT_PROMPT.format(
            resume_summary=resume_summary,
            jd_summary=jd_summary,
            conversation_history=conversation_history,
            answer_evaluations=answer_evaluations,
        )
        response = await self.llm.ainvoke(prompt)
        try:
            result = json.loads(response.content)
            logger.info(
                "Final report generated",
                overall_score=result.get("overall_score"),
            )
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse final report JSON")
            return {"overall_score": 0, "summary": "评估生成失败", "raw": response.content}
