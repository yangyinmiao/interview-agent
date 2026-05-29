"""Agent base class with LLM and tool registration."""

import re
import json
from typing import Optional, Any
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from app.services.llm_factory import get_llm


class BaseAgent:
    """Base class for all agents in the interview system."""

    def __init__(self, llm: Optional[BaseChatModel] = None, tools: Optional[list[BaseTool]] = None):
        self._llm = llm
        self.tools = tools or []

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def invoke_llm(self, prompt: str, response_format: str = "text") -> str:
        """Invoke LLM with a prompt and return response."""
        response = await self.llm.ainvoke(prompt)
        return response.content

    @staticmethod
    def extract_json(text: str) -> Any:
        """Robustly extract JSON from LLM response.

        Handles:
        - Plain JSON
        - Markdown code blocks: ```json ... ``` or ``` ... ```
        - Leading/trailing whitespace
        - Extra text before/after the JSON object
        """
        if not text:
            return None

        # Strip markdown code fences
        stripped = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped.strip())

        # Try direct parse first
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object/array anywhere in the text
        for pattern in (r'\{.*\}', r'\[.*\]'):
            match = re.search(pattern, stripped, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        return None

    def get_tools(self) -> list[BaseTool]:
        return self.tools
