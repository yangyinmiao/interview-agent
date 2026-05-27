import pytest
from unittest.mock import patch
from langchain_openai import ChatOpenAI
from app.services.llm_factory import get_llm, get_embeddings, get_llm_small, SimpleEmbeddings

MOCK_SETTINGS = {
    "llm_base_url": "https://test.api.example.com/v1",
    "llm_model_id": "test-model",
    "llm_api_key": "sk-test-key",
    "llm_temperature": 0.7,
    "llm_small_model_id": "test-model-small",
    "embedding_base_url": "https://test.emb.example.com/v1",
    "embedding_model_id": "test-emb-model",
    "embedding_api_key": "sk-test-emb-key",
}


class TestLLMFactory:
    @pytest.fixture(autouse=True)
    def mock_settings(self):
        with patch.multiple(
            "app.services.llm_factory.settings",
            **{k: v for k, v in MOCK_SETTINGS.items()}
        ):
            yield

    def test_get_llm_returns_chat_openai(self):
        llm = get_llm()
        assert isinstance(llm, ChatOpenAI)

    def test_get_embeddings_returns_simple_embeddings(self):
        emb = get_embeddings()
        assert isinstance(emb, SimpleEmbeddings)

    def test_get_llm_small_returns_chat_openai(self):
        llm = get_llm_small()
        assert isinstance(llm, ChatOpenAI)

    def test_get_llm_small_uses_different_model(self):
        llm = get_llm_small()
        assert llm.model_name != get_llm().model_name

    def test_get_llm_uses_configured_model(self):
        llm = get_llm()
        assert llm.model_name == "test-model"
