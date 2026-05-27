"""Resume analysis agent using LangGraph tools."""

import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.models.resume import Resume
from app.prompts.evaluation import RESUME_ANALYSIS_PROMPT


class ResumeAgent(BaseAgent):
    """Agent responsible for parsing and analyzing resumes."""

    def __init__(self, db: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def extract_structured_info(self, raw_text: str) -> dict:
        """Extract structured information from resume text using LLM."""
        prompt = RESUME_ANALYSIS_PROMPT.format(raw_text=raw_text)
        response = await self.invoke_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response", "raw": response}

    async def run(self, resume_id: str, tenant_id: str) -> dict:
        """Main agent flow: fetch resume, analyze it, return structured data."""
        result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.tenant_id == tenant_id)
        )
        resume = result.scalar_one_or_none()
        if not resume:
            return {"error": "Resume not found"}

        if not resume.raw_text:
            return {"error": "Resume raw_text is empty, file may not be parsed yet"}

        analysis = await self.extract_structured_info(resume.raw_text)

        if "error" not in analysis:
            resume.structured = analysis
            resume.parse_status = "completed"
            await self.db.flush()

        return analysis
