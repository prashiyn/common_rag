import pytest

from raqe.backtesting.replay_runner import run_backtest_scenarios


def test_replay_runner_produces_aggregate_and_collection_metrics() -> None:
    scenarios = [
        {
            "id": "s1",
            "question": "Why revenue increased?",
            "collection": "RELIANCE",
            "expected": {"min_confidence": 0.4, "must_include_terms": ["revenue"], "max_unresolved_references": 0},
        },
        {
            "id": "s2",
            "question": "Why margins changed?",
            "collection": "INFY",
            "expected": {"min_confidence": 0.2, "must_include_terms": ["margin"], "max_unresolved_references": 1},
        },
    ]

    def fake_query_runner(question: str, collection: str, section_hint=None):  # noqa: ARG001
        if collection == "RELIANCE":
            return {
                "answer": {"direct_answer": "Revenue improved in q1", "confidence": 0.8},
                "execution": {"references": [], "tables": [{"collection_id": "RELIANCE"}]},
            }
        return {
            "answer": {"direct_answer": "Margin changed", "confidence": 0.6},
            "execution": {"references": [{"reference_text": "Table 3", "resolved": False}], "tables": []},
        }

    result = run_backtest_scenarios(scenarios, query_runner=fake_query_runner)
    assert result["run_summary"]["scenario_count"] == 2
    assert "aggregate_metrics" in result
    assert "collection_metrics" in result
    assert set(result["collection_metrics"].keys()) == {"RELIANCE", "INFY"}


def test_replay_runner_continue_on_error() -> None:
    scenarios = [
        {"id": "s1", "question": "Q1", "collection": "RELIANCE"},
        {"id": "s2", "question": "Q2", "collection": "RELIANCE"},
    ]

    def flaky_runner(question: str, collection: str, section_hint=None):  # noqa: ARG001
        if question == "Q1":
            raise RuntimeError("failure")
        return {
            "answer": {"direct_answer": "ok", "confidence": 0.5},
            "execution": {"references": [], "tables": []},
        }

    result = run_backtest_scenarios(scenarios, query_runner=flaky_runner)
    assert result["run_summary"]["error_count"] == 1
    assert result["run_summary"]["success_count"] == 1


def test_replay_runner_threshold_breaches_detected() -> None:
    scenarios = [
        {"id": "s1", "question": "Q1", "collection": "RELIANCE", "expected": {"must_include_terms": ["revenue"]}},
    ]

    def weak_runner(question: str, collection: str, section_hint=None):  # noqa: ARG001
        return {
            "answer": {"direct_answer": "generic", "confidence": 0.1},
            "execution": {"references": [{"reference_text": "T1", "resolved": False}], "tables": []},
        }

    result = run_backtest_scenarios(
        scenarios,
        thresholds={"min_pass_rate": 1.0, "max_unresolved_reference_rate": 0.0, "min_average_confidence": 0.9},
        query_runner=weak_runner,
    )
    assert result["regression_status"]["passed"] is False
    assert len(result["regression_status"]["breached_thresholds"]) >= 1


def test_replay_runner_rejects_invalid_scenarios() -> None:
    with pytest.raises(ValueError, match="scenario question is required"):
        run_backtest_scenarios([{"id": "s1", "collection": "RELIANCE"}], query_runner=lambda **kwargs: {})  # noqa: ARG005
