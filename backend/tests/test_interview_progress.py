from datetime import datetime, timezone

from app.interview.progress import build_progress_trend


def test_progress_trend_compares_reports_and_topics():
    now = datetime.now(timezone.utc)
    result = build_progress_trend(
        [
            {"interview_id": "one", "completed_at": now, "overall_score": 6, "scores": {"communication": 5}},
            {"interview_id": "two", "completed_at": now, "overall_score": 8, "scores": {"communication": 7}},
        ],
        [
            {"topic": "database", "score": 5},
            {"topic": "database", "score": 8},
            {"topic": "network", "score": 7},
        ],
    )

    assert result["completed_count"] == 2
    assert result["overall_change"] == 2
    assert result["dimension_changes"]["communication"] == 2
    assert result["topics"][0] == {
        "topic": "database",
        "attempts": 2,
        "average_score": 6.5,
        "latest_score": 8.0,
        "change": 3.0,
    }
