"""Question Bank agent for RAG-based question retrieval."""

from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.agents.base import BaseAgent
from app.services.llm_factory import get_embeddings


class QBankAgent(BaseAgent):
    """Agent responsible for question bank management and retrieval."""

    def __init__(self, qdrant: QdrantClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qdrant = qdrant
        self.embeddings = get_embeddings()

    async def search_questions(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """Search questions from Qdrant using semantic similarity."""
        query_vector = self.embeddings.embed_query(query)

        results = self.qdrant.search(
            collection_name="questions",
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                ]
            ),
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "question": r.payload.get("question", ""),
                "answer": r.payload.get("answer", ""),
                "tags": r.payload.get("tags", []),
                "difficulty": r.payload.get("difficulty", "medium"),
            }
            for r in results
        ]

    async def search_by_topic(
        self, topic: str, tenant_id: str, top_k: int = 5
    ) -> list[dict]:
        """Search questions by topic tag."""
        query_vector = self.embeddings.embed_query(topic)
        results = self.qdrant.search(
            collection_name="questions",
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                ]
            ),
            limit=top_k,
        )
        return [
            {
                "id": str(r.id),
                "question": r.payload.get("question", ""),
                "answer": r.payload.get("answer", ""),
                "tags": r.payload.get("tags", []),
                "difficulty": r.payload.get("difficulty", "medium"),
            }
            for r in results
        ]

    async def search(
        self,
        question_bank_id: str,
        tenant_id: str,
        context: str = "",
        top_k: int = 5,
    ) -> list[dict]:
        """Retrieve relevant questions for interview context."""
        try:
            search_query = context or "general interview questions"

            questions = await self.search_questions(
                query=search_query,
                tenant_id=tenant_id,
                top_k=top_k,
            )

            if not questions:
                questions = await self.search_by_topic(
                    topic=search_query,
                    tenant_id=tenant_id,
                    top_k=top_k,
                )

            return questions
        except Exception as e:
            import logging
            _logger = logging.getLogger("agents.qbank")
            _logger.warning(f"QBank search failed, returning empty: {e}")
            return []
