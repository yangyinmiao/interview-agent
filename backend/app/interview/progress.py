"""Build a tenant's Progress Trend from persisted reports and evaluations."""

from __future__ import annotations

from collections import defaultdict


def build_progress_trend(report_rows: list[dict], evaluation_rows: list[dict]) -> dict:
    points = [
        {
            "interview_id": row["interview_id"],
            "completed_at": row["completed_at"],
            "overall_score": _number(row.get("overall_score")),
            "scores": row.get("scores") or {},
        }
        for row in report_rows
    ]
    scored_points = [point for point in points if point["overall_score"] is not None]
    overall_change = None
    dimension_changes: dict[str, float] = {}
    if len(scored_points) >= 2:
        overall_change = round(
            scored_points[-1]["overall_score"] - scored_points[0]["overall_score"], 2
        )
        first_scores = scored_points[0]["scores"]
        latest_scores = scored_points[-1]["scores"]
        for dimension in first_scores.keys() & latest_scores.keys():
            dimension_changes[dimension] = round(
                _number(latest_scores[dimension]) - _number(first_scores[dimension]), 2
            )

    topic_scores: dict[str, list[float]] = defaultdict(list)
    for evaluation in evaluation_rows:
        topic = evaluation.get("topic")
        score = _number(evaluation.get("score"))
        if topic and score is not None:
            topic_scores[topic].append(score)

    topics = [
        {
            "topic": topic,
            "attempts": len(scores),
            "average_score": round(sum(scores) / len(scores), 2),
            "latest_score": scores[-1],
            "change": round(scores[-1] - scores[0], 2) if len(scores) >= 2 else None,
        }
        for topic, scores in topic_scores.items()
    ]
    topics.sort(key=lambda item: (-item["attempts"], item["topic"]))

    return {
        "interviews": points,
        "completed_count": len(points),
        "overall_change": overall_change,
        "dimension_changes": dimension_changes,
        "topics": topics,
    }


def _number(value):
    return float(value) if value is not None else None
