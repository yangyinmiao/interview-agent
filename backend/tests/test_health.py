from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok_when_models_are_available():
    model_status = {
        "llm": {"status": "ok", "model": "llm", "latency_ms": 1},
        "embedding": {
            "status": "ok",
            "model": "embedding",
            "latency_ms": 1,
            "dimension": 3,
        },
    }
    with patch("app.main.check_model_health", AsyncMock(return_value=model_status)):
        response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["components"] == model_status


def test_health_returns_503_when_a_model_is_unavailable():
    model_status = {
        "llm": {"status": "error", "model": "llm", "latency_ms": 1, "error": "boom"},
        "embedding": {
            "status": "ok",
            "model": "embedding",
            "latency_ms": 1,
            "dimension": 3,
        },
    }
    with patch("app.main.check_model_health", AsyncMock(return_value=model_status)):
        response = TestClient(create_app()).get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
