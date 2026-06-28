"""Deterministic baseline metrics for exported Practice Interviews."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


REQUIRED_EVALUATION_FIELDS = {
    "score",
    "technical_accuracy",
    "depth_breadth",
    "clarity",
    "practical_experience",
    "brief_feedback",
    "topic",
    "should_follow_up",
}


def evaluate_interview_quality(rounds: list[dict]) -> dict:
    """Return stable metrics that can gate prompt and orchestration changes."""
    if not rounds:
        return {
            "round_integrity": 0.0,
            "evaluation_completeness": 0.0,
            "question_repetition_rate": 0.0,
            "topic_coverage": 0,
            "score_variance": 0.0,
            "passed": False,
        }

    intact = sum(
        bool(item.get("q") and item.get("a") and item.get("evaluation"))
        for item in rounds
    )
    complete = sum(
        REQUIRED_EVALUATION_FIELDS.issubset((item.get("evaluation") or {}).keys())
        for item in rounds
    )
    repeated_pairs = sum(
        _question_similarity(left.get("q", ""), right.get("q", "")) >= 0.72
        for index, left in enumerate(rounds)
        for right in rounds[index + 1 :]
    )
    pair_count = len(rounds) * (len(rounds) - 1) / 2
    repetition_rate = repeated_pairs / pair_count if pair_count else 0.0
    topics = {
        item.get("evaluation", {}).get("topic")
        for item in rounds
        if item.get("evaluation", {}).get("topic")
    }
    scores = [
        float(item["evaluation"]["score"])
        for item in rounds
        if item.get("evaluation", {}).get("score") is not None
    ]
    variance = _variance(scores)
    round_integrity = intact / len(rounds)
    evaluation_completeness = complete / len(rounds)

    return {
        "round_integrity": round(round_integrity, 4),
        "evaluation_completeness": round(evaluation_completeness, 4),
        "question_repetition_rate": round(repetition_rate, 4),
        "topic_coverage": len(topics),
        "topic_distribution": dict(Counter(
            item.get("evaluation", {}).get("topic")
            for item in rounds
            if item.get("evaluation", {}).get("topic")
        )),
        "score_variance": round(variance, 4),
        "passed": (
            round_integrity == 1.0
            and evaluation_completeness == 1.0
            and repetition_rate <= 0.15
        ),
    }


def _question_similarity(left: str, right: str) -> float:
    left_terms = set(_ngrams(left))
    right_terms = set(_ngrams(right))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def _ngrams(text: str, size: int = 3) -> Iterable[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    if len(normalized) <= size:
        return [normalized] if normalized else []
    return (normalized[index : index + size] for index in range(len(normalized) - size + 1))


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)
