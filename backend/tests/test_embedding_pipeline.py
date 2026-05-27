import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.embedding_pipeline import EmbeddingPipeline


class TestEmbeddingPipeline:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def pipeline(self, mock_db):
        with patch("app.services.embedding_pipeline.get_embeddings"), \
             patch("app.services.embedding_pipeline.get_qdrant"):
            return EmbeddingPipeline(db=mock_db)

    @pytest.mark.asyncio
    async def test_save_chunks_adds_chunks(self, pipeline, mock_db):
        chunks = [
            {"index": 0, "content": "Chunk 1 content"},
            {"index": 1, "content": "Chunk 2 content"},
            {"index": 2, "content": "Chunk 3 content"},
        ]
        await pipeline.save_chunks(
            tenant_id="f64ac857-8ee0-487a-a527-7399aff8ad93",
            source_type="resume",
            source_id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
            chunks=chunks,
        )
        assert mock_db.add.call_count == 3

    @pytest.mark.asyncio
    async def test_process_chunks_no_pending(self, pipeline, mock_db):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result

        await pipeline.process_chunks(
            source_type="resume",
            source_id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
        )
        mock_db.execute.assert_called_once()

    def test_trigger_embedding_dispatches_celery_task(self, pipeline):
        with patch("app.tasks.embedding_tasks.embed_source_chunks") as mock_task:
            pipeline.trigger_embedding(
                source_type="resume",
                source_id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
            )
            mock_task.delay.assert_called_once_with(
                source_type="resume",
                source_id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
            )
