"""Document processing LangGraph for upload → parse → chunk → save → embed."""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from app.graphs.states import DocumentState


def build_document_graph() -> CompiledStateGraph:
    """Build document processing graph. Note: embedding is delegated to Celery."""

    workflow = StateGraph(DocumentState)

    async def parse_document(state: DocumentState) -> DocumentState:
        """Parse uploaded document into raw text."""
        from app.services.document_parser import DocumentParser

        parser = DocumentParser()
        raw_text = await parser.parse(state.get("file_bytes"), state.get("filename", ""))
        state["raw_text"] = raw_text
        state["status"] = "parsed"
        return state

    async def chunk_text(state: DocumentState) -> DocumentState:
        """Split text into chunks."""
        from app.services.document_parser import Chunker

        chunker = Chunker()
        strategy = state.get("source_type", "resume")
        chunks = chunker.chunk(state.get("raw_text", ""), strategy)
        state["chunks"] = [{"index": i, "content": c} for i, c in enumerate(chunks)]
        state["status"] = "chunked"
        return state

    async def save_chunks(state: DocumentState) -> DocumentState:
        """Save chunks to PostgreSQL and trigger Celery embedding task."""
        from app.services.embedding_pipeline import EmbeddingPipeline
        from app.core.database import async_session_factory

        async with async_session_factory() as db:
            pipeline = EmbeddingPipeline(db)
            await pipeline.save_chunks(
                tenant_id=state["tenant_id"],
                source_type=state["source_type"],
                source_id=state["source_id"],
                chunks=state.get("chunks", []),
            )
            # Trigger async embedding
            pipeline.trigger_embedding(
                source_type=state["source_type"],
                source_id=state["source_id"],
            )

        state["status"] = "saved"
        return state

    workflow.add_node("parse", parse_document)
    workflow.add_node("chunk", chunk_text)
    workflow.add_node("save", save_chunks)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "chunk")
    workflow.add_edge("chunk", "save")
    workflow.add_edge("save", END)

    return workflow.compile()
