"""Supervisor agent for routing decisions in the interview graph."""

from app.agents.base import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent that makes routing decisions in the interview workflow."""

    def router(self, state: dict) -> str:
        """Determine next step based on current interview state."""
        round_count = state.get("round_count", 0)
        max_rounds = state.get("max_rounds", 10)
        interview_mode = state.get("interview_mode", "basic")
        follow_up_depth = state.get("follow_up_depth", 0)
        answer_evaluations = state.get("answer_evaluations", [])

        # Check if we should end
        if round_count >= max_rounds:
            return "end"

        last_eval = answer_evaluations[-1] if answer_evaluations else None

        # Follow-up mode: continue probing if score is low
        if interview_mode == "follow_up" and follow_up_depth < 3:
            if last_eval:
                score = last_eval.get("score", 5)
                if score < 7:
                    return "ask"

        # Stress mode: keep challenging
        if interview_mode == "stress":
            return "ask"

        # Default: continue with new topic
        return "ask"
