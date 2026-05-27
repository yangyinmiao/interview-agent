"""JD analysis agent."""

import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.base import BaseAgent
from app.models.jd import JD
from app.prompts.evaluation import JD_ANALYSIS_PROMPT


class JDAgent(BaseAgent):
    """Agent responsible for parsing and analyzing job descriptions."""

    def __init__(self, db: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db

    async def extract_requirements(self, raw_text: str) -> dict:
        """Extract structured requirements from JD text using LLM."""
        prompt = JD_ANALYSIS_PROMPT.format(raw_text=raw_text)
        response = await self.invoke_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response", "raw": response}

    async def run(self, jd_id: str, tenant_id: str) -> dict:
        """Main agent flow: fetch JD, analyze it, return structured data."""
        result = await self.db.execute(
            select(JD).where(JD.id == jd_id, JD.tenant_id == tenant_id)
        )
        jd = result.scalar_one_or_none()
        if not jd:
            return {"error": "JD not found"}

        if not jd.raw_text:
            return {"error": "JD raw_text is empty, file may not be parsed yet"}

        analysis = await self.extract_requirements(jd.raw_text)

        if "error" not in analysis:
            jd.structured = analysis
            jd.parse_status = "completed"
            await self.db.flush()

        return analysis
