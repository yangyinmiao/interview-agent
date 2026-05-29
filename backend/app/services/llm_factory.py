from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()


def get_llm() -> BaseChatModel:
    """Return an LLM instance without baked-in callbacks.
    Tracing is handled at the graph invocation level via per-request handlers."""
    return ChatOpenAI(
        model=settings.llm_model_id,
        temperature=settings.llm_temperature,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


class SimpleEmbeddings(Embeddings):
    """Minimal OpenAI-compatible embeddings that sends raw text, avoiding
    LangChain's tiktoken pre-tokenization which breaks with custom proxies."""

    def __init__(self, model: str, base_url: str, api_key: str):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Batch at most 20 texts per request to avoid oversized payloads
        all_embeddings: List[List[float]] = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = self.client.embeddings.create(model=self.model, input=batch)
            # Sort by index to preserve input order
            sorted_data = sorted(resp.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        resp = self.client.embeddings.create(model=self.model, input=[text])
        return resp.data[0].embedding


def get_embeddings() -> Embeddings:
    return SimpleEmbeddings(
        model=settings.embedding_model_id,
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key or settings.llm_api_key,
    )


def get_llm_small() -> BaseChatModel:
    """Return a lightweight LLM instance without baked-in callbacks."""
    return ChatOpenAI(
        model=settings.llm_small_model_id,
        temperature=0.3,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


def get_langfuse_handler(session_id: Optional[str] = None) -> CallbackHandler:
    """Create a Langfuse CallbackHandler.

    Pass session_id (e.g. interview_id) so all LLM calls in the same
    interview are grouped together in Langfuse.
    """
    s = get_settings()
    return CallbackHandler(
        secret_key=s.langfuse_secret_key,
        public_key=s.langfuse_public_key,
        host=s.langfuse_host,
        session_id=session_id,
    )
