from app.quality.interview_quality import evaluate_interview_quality


def evaluation(score, topic):
    return {
        "score": score,
        "technical_accuracy": score,
        "depth_breadth": score,
        "clarity": score,
        "practical_experience": score,
        "brief_feedback": "evidence-based feedback",
        "topic": topic,
        "should_follow_up": False,
    }


def test_quality_baseline_accepts_complete_diverse_rounds():
    result = evaluate_interview_quality([
        {"q": "Explain transaction isolation.", "a": "A1", "evaluation": evaluation(8, "database")},
        {"q": "How do you make a request idempotent?", "a": "A2", "evaluation": evaluation(7, "distributed systems")},
        {"q": "Describe a production incident you handled.", "a": "A3", "evaluation": evaluation(6, "project experience")},
    ])

    assert result["passed"] is True
    assert result["topic_coverage"] == 3
    assert result["question_repetition_rate"] == 0


def test_quality_baseline_rejects_repeated_or_incomplete_rounds():
    incomplete = {"score": 5, "topic": "database"}
    result = evaluate_interview_quality([
        {"q": "What is a database index?", "a": "A1", "evaluation": incomplete},
        {"q": "What is a database index?", "a": "A2", "evaluation": incomplete},
    ])

    assert result["passed"] is False
    assert result["evaluation_completeness"] == 0
    assert result["question_repetition_rate"] == 1
