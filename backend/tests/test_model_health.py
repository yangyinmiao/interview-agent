from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.model_health import check_model_health


@pytest.fixture
def health_settings():
    return Mock(
        llm_model_id="test-llm",
        embedding_model_id="test-embedding",
        embedding_dimension=3,
        model_health_check_timeout_seconds=1,
        llm_api_key="secret-llm",
        embedding_api_key="secret-embedding",
    )


@pytest.mark.asyncio
async def test_model_health_checks_real_llm_and_embedding_calls(health_settings):
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value=Mock(content="OK"))
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    with (
        patch("app.services.model_health.get_settings", return_value=health_settings),
        patch("app.services.model_health.get_llm", return_value=llm),
        patch("app.services.model_health.get_embeddings", return_value=embeddings),
    ):
        result = await check_model_health()

    assert result["llm"]["status"] == "ok"
    assert result["embedding"]["status"] == "ok"
    assert result["embedding"]["dimension"] == 3
    llm.ainvoke.assert_awaited_once_with("Reply with OK.")
    embeddings.embed_query.assert_called_once_with("health check")


@pytest.mark.asyncio
async def test_model_health_reports_failures_and_dimension_mismatch(health_settings):
    llm = Mock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("bad secret-llm"))
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1, 0.2]

    with (
        patch("app.services.model_health.get_settings", return_value=health_settings),
        patch("app.services.model_health.get_llm", return_value=llm),
        patch("app.services.model_health.get_embeddings", return_value=embeddings),
    ):
        result = await check_model_health()

    assert result["llm"]["status"] == "error"
    assert "secret-llm" not in result["llm"]["error"]
    assert result["embedding"]["status"] == "error"
    assert "expected 3, got 2" in result["embedding"]["error"]


@pytest.mark.asyncio
async def test_model_health_rejects_empty_llm_response(health_settings):
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value=Mock(content=""))
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

    with (
        patch("app.services.model_health.get_settings", return_value=health_settings),
        patch("app.services.model_health.get_llm", return_value=llm),
        patch("app.services.model_health.get_embeddings", return_value=embeddings),
    ):
        result = await check_model_health()

    assert result["llm"]["status"] == "error"
    assert "empty response" in result["llm"]["error"]
