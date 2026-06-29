"""Runtime health checks for the configured LLM and embedding models."""

import asyncio
import time
from typing import Any, Awaitable, Callable

from app.core.config import get_settings
from app.services.llm_factory import get_embeddings, get_llm


LLM_HEALTH_PROMPT = "Reply with OK."
EMBEDDING_HEALTH_TEXT = "health check"


def _safe_error(exc: Exception) -> str:
    """Return a useful error without leaking configured API keys."""
    settings = get_settings()
    message = str(exc)
    for secret in (settings.llm_api_key, settings.embedding_api_key):
        if secret:
            message = message.replace(secret, "***")
    return message[:500]


async def _run_check(
    model: str,
    check: Callable[[], Awaitable[dict[str, Any]]],
    timeout_seconds: float,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        details = await asyncio.wait_for(check(), timeout=timeout_seconds)
        return {
            "status": "ok",
            "model": model,
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
            **details,
        }
    except Exception as exc:
        return {
            "status": "error",
            "model": model,
            "latency_ms": round((time.perf_counter() - started_at) * 1000),
            "error": f"{type(exc).__name__}: {_safe_error(exc)}",
        }


async def _check_llm() -> dict[str, Any]:
    response = await get_llm().ainvoke(LLM_HEALTH_PROMPT)
    if response is None or not getattr(response, "content", None):
        raise RuntimeError("LLM returned an empty response")
    return {}


async def _check_embedding() -> dict[str, Any]:
    vector = await asyncio.to_thread(
        get_embeddings().embed_query,
        EMBEDDING_HEALTH_TEXT,
    )
    if not vector:
        raise RuntimeError("Embedding model returned an empty vector")

    expected_dimension = get_settings().embedding_dimension
    if len(vector) != expected_dimension:
        raise RuntimeError(
            "Embedding dimension mismatch: "
            f"expected {expected_dimension}, got {len(vector)}"
        )
    return {"dimension": len(vector)}


async def check_model_health() -> dict[str, dict[str, Any]]:
    """Make minimal real requests to both configured model endpoints."""
    settings = get_settings()
    llm, embedding = await asyncio.gather(
        _run_check(
            settings.llm_model_id,
            _check_llm,
            settings.model_health_check_timeout_seconds,
        ),
        _run_check(
            settings.embedding_model_id,
            _check_embedding,
            settings.model_health_check_timeout_seconds,
        ),
    )
    return {"llm": llm, "embedding": embedding}
