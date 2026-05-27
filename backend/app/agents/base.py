"""Agent base class with LLM and tool registration."""

from typing import Optional
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

    def get_tools(self) -> list[BaseTool]:
        return self.tools
