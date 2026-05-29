"""Interviewer agent - the core interview conversation driver."""

import json
from typing import Optional
from app.agents.base import BaseAgent
from app.prompts.interview_modes import get_interview_prompt
from app.core.logging import get_structured_logger

logger = get_structured_logger("agents.interviewer")


class InterviewerAgent(BaseAgent):
    """Agent responsible for generating interview questions and managing the conversation."""

    async def generate_question(
        self,
        mode: str,
        resume_analysis: Optional[dict],
        jd_analysis: Optional[dict],
        retrieved_questions: Optional[list[dict]],
        question_history: list[dict],
        follow_up_depth: int,
        round_count: int,
        max_rounds: int,
        last_evaluation: Optional[dict] = None,
    ) -> dict:
        """Generate the next interview question based on mode and context."""

        resume_summary = self._format_resume(resume_analysis)
        jd_summary = self._format_jd(jd_analysis)
        questions_ref = self._format_questions(retrieved_questions)
        topics = self._extract_topics(question_history)

        logger.info(
            f"Generating question for mode={mode}",
            mode=mode,
            round_count=round_count,
            max_rounds=max_rounds,
            follow_up_depth=follow_up_depth,
            topics_covered=topics,
            has_resume=resume_analysis is not None,
            has_jd=jd_analysis is not None,
            retrieved_question_count=len(retrieved_questions) if retrieved_questions else 0,
        )

        prompt_template = get_interview_prompt(mode)
        prompt = prompt_template.format(
            resume_summary=resume_summary,
            jd_summary=jd_summary,
            retrieved_questions=questions_ref,
            round_count=round_count,
            max_rounds=max_rounds,
            topics_covered=topics,
            follow_up_depth=follow_up_depth,
            last_evaluation=json.dumps(last_evaluation, ensure_ascii=False) if last_evaluation else "无",
        )

        # For the very first question, instruct the LLM to open with a brief greeting
        if round_count == 0 and not question_history:
            prompt = '【面试开场】这是面试的第一个问题。请先用一句简短友好的开场白（如"你好，欢迎参加本次面试，我们先从...开始"），然后直接提出第一个问题。\n\n' + prompt

        if question_history:
            history_text = "\n---\n".join(
                f"第{i+1}轮 - 面试官: {h['q']}\n候选人: {h['a']}"
                for i, h in enumerate(question_history[-5:])
            )
            prompt += f"\n\n## 最近对话历史\n{history_text}\n\n请根据以上对话历史，提出下一个问题。"

        prompt += "\n\n请以JSON格式返回:\n{\"question\": \"你的问题\", \"topic\": \"话题类别\", \"difficulty\": \"easy/medium/hard\"}"

        response = await self.invoke_llm(prompt)

        result = self.extract_json(response)
        if result and isinstance(result, dict) and result.get("question"):
            logger.info(
                "Question generated",
                question_preview=result.get("question", "")[:100],
                topic=result.get("topic", "unknown"),
                difficulty=result.get("difficulty", "medium"),
            )
            return result
        logger.warning("Failed to parse question JSON, using raw response")
        return {"question": response.strip(), "topic": "general", "difficulty": "medium"}

    def _format_resume(self, analysis: Optional[dict]) -> str:
        if not analysis:
            return "未提供简历信息"
        if "error" in analysis:
            return "简历分析尚未完成"
        return json.dumps(analysis, ensure_ascii=False, indent=2)

    def _format_jd(self, analysis: Optional[dict]) -> str:
        if not analysis:
            return "未提供JD信息"
        if "error" in analysis:
            return "JD分析尚未完成"
        return json.dumps(analysis, ensure_ascii=False, indent=2)

    def _format_questions(self, questions: Optional[list[dict]]) -> str:
        if not questions:
            return "暂无匹配的题库参考"
        items = [f"- [{q.get('difficulty', 'medium')}] {q.get('question', '')}" for q in questions[:5]]
        return "\n".join(items)

    def _extract_topics(self, history: list[dict]) -> str:
        if not history:
            return "尚未提问"
        topics = {h.get("topic", "未分类") for h in history if "topic" in h}
        return ", ".join(topics) if topics else "综合面试"

    async def generate_reference_answer(self, question: str, context: str = "") -> str:
        """Generate a high-quality reference answer for learning mode."""
        context_block = f"\n\n## 背景上下文\n{context}" if context else ""
        prompt = f"""你是一位资深技术面试官。请为以下面试问题生成一份高质量的参考答案。

## 面试问题
{question}
{context_block}

## 参考答案要求
1. 技术准确，覆盖关键知识点
2. 结构清晰，有逻辑层次
3. 长度适中，2-4 段即可
4. 如果涉及代码，给出简洁示例

请直接输出参考答案，不需要 JSON 格式。"""

        response = await self.invoke_llm(prompt)
        return response.strip()
