import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.graphs.states import InterviewState
from app.agents.supervisor import SupervisorAgent


class TestSupervisorRouter:
    @pytest.fixture
    def supervisor(self):
        return SupervisorAgent()

    def _make_state(self, **overrides):
        state = {
            "tenant_id": "test-tenant",
            "interview_id": "test-interview",
            "resume_id": "",
            "jd_id": "",
            "question_bank_id": "",
            "interview_mode": "basic",
            "max_rounds": 10,
            "resume_analysis": None,
            "jd_analysis": None,
            "retrieved_questions": [],
            "current_question": "",
            "current_answer": "",
            "question_history": [],
            "follow_up_depth": 0,
            "round_count": 0,
            "answer_evaluations": [],
            "final_report": None,
            "messages": [],
            "next_action": "prepare",
        }
        state.update(overrides)
        return state

    def test_asks_when_below_max_rounds(self, supervisor):
        state = self._make_state(round_count=3, max_rounds=10)
        result = supervisor.router(state)
        assert result == "ask"

    def test_ends_when_max_rounds_reached(self, supervisor):
        state = self._make_state(round_count=10, max_rounds=10)
        result = supervisor.router(state)
        assert result == "end"

    def test_ends_when_over_max_rounds(self, supervisor):
        state = self._make_state(round_count=11, max_rounds=10)
        result = supervisor.router(state)
        assert result == "end"

    def test_follow_up_mode_asks_on_low_score(self, supervisor):
        state = self._make_state(
            interview_mode="follow_up",
            follow_up_depth=0,
            round_count=2,
            max_rounds=10,
            answer_evaluations=[{"score": 3}],
        )
        result = supervisor.router(state)
        assert result == "ask"

    def test_stress_mode_always_asks(self, supervisor):
        state = self._make_state(
            interview_mode="stress",
            round_count=5,
            max_rounds=10,
        )
        result = supervisor.router(state)
        assert result == "ask"


class TestGraphBuild:
    def test_graph_builds_without_error(self):
        mock_db = AsyncMock()
        with patch("app.core.qdrant.get_qdrant"), \
             patch("app.services.llm_factory.settings.llm_api_key", "sk-test"), \
             patch("app.services.llm_factory.settings.llm_base_url", "https://test.example.com/v1"), \
             patch("app.services.llm_factory.settings.llm_model_id", "test-model"), \
             patch("app.services.llm_factory.settings.llm_small_model_id", "test-small"), \
             patch("app.services.llm_factory.settings.llm_temperature", 0.7), \
             patch("app.services.llm_factory.settings.embedding_api_key", "sk-test"), \
             patch("app.services.llm_factory.settings.embedding_base_url", "https://test.example.com/v1"), \
             patch("app.services.llm_factory.settings.embedding_model_id", "test-emb"):
            from app.graphs.interview_graph import build_interview_graph
            graph = build_interview_graph(mock_db)
            assert graph is not None
