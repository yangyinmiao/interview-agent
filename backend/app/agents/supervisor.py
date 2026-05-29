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

        # Always end at max rounds
        if round_count >= max_rounds:
            return "end"

        last_eval = answer_evaluations[-1] if answer_evaluations else None

        if interview_mode == "follow_up":
            # Continue follow-up chain if evaluator says so AND depth < 3
            if last_eval and last_eval.get("should_follow_up") and follow_up_depth < 3:
                return "ask"
            # Otherwise move to next topic (still ask)
            return "ask"

        if interview_mode == "stress":
            # In stress mode, always challenge — but respect max_rounds
            return "ask"

        if interview_mode == "deep":
            # Deep mode: follow evaluator's signal for whether to drill deeper
            if last_eval and last_eval.get("should_follow_up") and follow_up_depth < 2:
                return "ask"
            return "ask"

        # basic and default
        return "ask"
