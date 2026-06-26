from __future__ import annotations

from raqe.agent.query_engine import run_query
from raqe.backtesting.metrics import (
    aggregate_metrics,
    collection_metrics,
    evaluate_regression_status,
    evaluate_scenario_result,
)


def _validate_scenario(scenario: dict) -> None:
    if not scenario.get("id"):
        raise ValueError("scenario id is required")
    if not scenario.get("question"):
        raise ValueError("scenario question is required")
    if not scenario.get("collection"):
        raise ValueError("scenario collection is required")


def run_backtest_scenarios(
    scenarios: list[dict],
    thresholds: dict | None = None,
    query_runner=run_query,
) -> dict:
    for scenario in scenarios:
        _validate_scenario(scenario)

    scenario_results = []
    scenario_metrics = []
    for scenario in scenarios:
        scenario_id = scenario["id"]
        try:
            result = query_runner(
                question=scenario["question"],
                collection=scenario["collection"],
                section_hint=scenario.get("section_hint"),
            )
            metric = evaluate_scenario_result(scenario, result)
            scenario_metrics.append(metric)
            scenario_results.append(
                {
                    "id": scenario_id,
                    "status": "ok",
                    "result": result,
                    "metrics": metric,
                    "failure_reason": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            scenario_results.append(
                {
                    "id": scenario_id,
                    "status": "error",
                    "result": None,
                    "metrics": {
                        "question": scenario["question"],
                        "collection": scenario["collection"],
                        "confidence": 0.0,
                        "reference_count": 0,
                        "unresolved_reference_count": 0,
                        "term_coverage": 0.0,
                        "missing_terms": [],
                        "scope_leakage_count": 0,
                        "passed": False,
                    },
                    "failure_reason": str(exc),
                }
            )

    aggregate = aggregate_metrics([entry["metrics"] for entry in scenario_results])
    per_collection = collection_metrics([entry["metrics"] for entry in scenario_results])
    regression = evaluate_regression_status(aggregate, thresholds=thresholds)

    return {
        "run_summary": {
            "scenario_count": len(scenarios),
            "success_count": len([s for s in scenario_results if s["status"] == "ok"]),
            "error_count": len([s for s in scenario_results if s["status"] == "error"]),
        },
        "aggregate_metrics": aggregate,
        "collection_metrics": per_collection,
        "scenario_results": scenario_results,
        "regression_status": regression,
    }
