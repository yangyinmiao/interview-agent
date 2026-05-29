"""Interviewer agent - the core interview conversation driver."""

import json
from typing import Optional, AsyncGenerator
from app.agents.base import BaseAgent
from app.prompts.interview_modes import get_interview_prompt
from app.services.llm_factory import get_llm_small
from app.core.logging import get_structured_logger

logger = get_structured_logger("agents.interviewer")


class InterviewerAgent(BaseAgent):
    """Agent responsible for generating interview questions and managing the conversation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._small_llm = None

    @property
    def small_llm(self):
        if self._small_llm is None:
            self._small_llm = get_llm_small()
        return self._small_llm

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
        prompt = self._build_question_prompt(
            mode=mode,
            resume_analysis=resume_analysis,
            jd_analysis=jd_analysis,
            retrieved_questions=retrieved_questions,
            question_history=question_history,
            follow_up_depth=follow_up_depth,
            round_count=round_count,
            max_rounds=max_rounds,
            last_evaluation=last_evaluation,
        )
        response = await self.small_llm.ainvoke(prompt)

        content = response.content if hasattr(response, 'content') else str(response)
        result = self.extract_json(content)
        if result and isinstance(result, dict) and result.get("question"):
            logger.info(
                "Question generated",
                question_preview=result.get("question", "")[:100],
                topic=result.get("topic", "unknown"),
                difficulty=result.get("difficulty", "medium"),
            )
            return result
        logger.warning("Failed to parse question JSON, using raw response")
        return {"question": content.strip(), "topic": "general", "difficulty": "medium"}

    async def astream_question(self, **kwargs) -> AsyncGenerator[str, None]:
        """Stream-generate the next interview question, yielding text chunks.
        Uses a plain-text prompt (no JSON) so tokens are directly displayable.
        """
        prompt = self._build_question_prompt(**kwargs)
        # Replace the JSON output instruction with plain text instruction
        prompt = prompt.replace(
            '\n请以JSON格式返回:\n{"question": "你的问题", "topic": "话题类别", "difficulty": "easy/medium/hard"}',
            '\n请直接输出面试问题，不要包含任何JSON格式或额外说明，只输出问题本身。'
        )
        async for chunk in self.small_llm.astream(prompt):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

    def _build_question_prompt(
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
    ) -> str:
        """Build the full prompt for question generation."""
        resume_summary = self._format_resume(resume_analysis)
        jd_summary = self._format_jd(jd_analysis)
        questions_ref = self._format_questions(retrieved_questions)
        topics = self._extract_topics(question_history)

        logger.info(
            f"Building question prompt for mode={mode}",
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
            prompt = prompt + '\n<instruction>这是面试的第一个问题。请先用一句简短友好的开场白（如"你好，欢迎参加本次面试，我们先从...开始"），然后直接提出第一个问题。</instruction>'

        if question_history:
            history_lines = []
            total_history = len(question_history)
            recent = question_history[-5:]
            offset = total_history - len(recent)  # rounds before the recent slice
            for i, h in enumerate(recent):
                history_lines.append(f"<round num=\"{offset + i + 1}\">\n<question>{h['q']}</question>\n<answer>{h['a']}</answer>\n</round>")
            history_text = "\n".join(history_lines)
            prompt += f"\n\n<history>\n{history_text}\n</history>"

        prompt += "\n\n请以JSON格式返回:\n{\"question\": \"你的问题\", \"topic\": \"话题类别\", \"difficulty\": \"easy/medium/hard\"}"
        return prompt

    def _format_resume(self, analysis: Optional[dict]) -> str:
        if not analysis:
            return "未提供简历信息"
        if "error" in analysis:
            return "简历分析尚未完成"

        # Extract only what the interviewer needs — skip full skill list and redundant data
        parts = []
        if analysis.get("profile_summary"):
            parts.append(f"背景: {analysis['profile_summary']}")
        if analysis.get("years_of_experience"):
            parts.append(f"经验: {analysis['years_of_experience']}")

        # Key strengths (max 3)
        strengths = analysis.get("key_strengths", [])
        if strengths:
            parts.append("核心优势: " + "; ".join(strengths[:3]))

        # Experience highlights (max 3 entries, 2 highlights each)
        exp_list = analysis.get("experience", [])
        if exp_list:
            exp_lines = []
            for exp in exp_list[:3]:
                highlights = exp.get("highlights", [])[:2]
                exp_lines.append(f"- {exp.get('role', '')} @ {exp.get('company', '')} ({exp.get('duration', '')}): {'; '.join(highlights)}")
            parts.append("经历:\n" + "\n".join(exp_lines))

        # Top skills (max 10)
        skills = analysis.get("skills", [])
        if skills:
            parts.append(f"技能: {', '.join(skills[:10])}")

        return "\n".join(parts)

    def _format_jd(self, analysis: Optional[dict]) -> str:
        if not analysis:
            return "未提供JD信息"
        if "error" in analysis:
            return "JD分析尚未完成"

        parts = []
        if analysis.get("title"):
            parts.append(f"职位: {analysis['title']}")
        if analysis.get("required_skills"):
            parts.append(f"必备技能: {', '.join(analysis['required_skills'][:8])}")
        if analysis.get("key_points"):
            parts.append(f"考察重点: {', '.join(analysis['key_points'])}")
        return "\n".join(parts) if parts else "JD分析数据不完整"

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
        context_block = f"\n<context>\n{context}\n</context>" if context else ""
        prompt = f"""你是一位资深技术面试官。请为以下面试问题生成一份高质量的参考答案。

<question>
{question}
</question>
{context_block}

<requirements>
1. 技术准确，覆盖关键知识点
2. 结构清晰，有逻辑层次
3. 长度适中，2-4 段即可
4. 如果涉及代码，给出简洁示例
</requirements>

请直接输出参考答案，不需要 JSON 格式。"""

        response = await self.small_llm.ainvoke(prompt)
        return response.content.strip() if hasattr(response, 'content') else str(response).strip()
