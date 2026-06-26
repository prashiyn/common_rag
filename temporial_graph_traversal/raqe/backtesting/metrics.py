from __future__ import annotations

from raqe.collection_namespace import to_internal


def evaluate_scenario_result(scenario: dict, result: dict) -> dict:
    expected = scenario.get("expected", {})
    question = scenario["question"]
    collection = scenario["collection"]
    internal_collection = to_internal(collection) or collection
    answer = result.get("answer", {})
    execution = result.get("execution", {})
    direct_answer = str(answer.get("direct_answer", "")).lower()
    confidence = float(answer.get("confidence", 0.0))
    must_include_terms = [term.lower() for term in expected.get("must_include_terms", [])]
    missing_terms = [term for term in must_include_terms if term not in direct_answer]

    references = execution.get("references", [])
    unresolved_count = len([ref for ref in references if ref.get("reference_text") and not ref.get("resolved", True)])
    reference_count = len(references)

    min_confidence = float(expected.get("min_confidence", 0.0))
    max_unresolved = int(expected.get("max_unresolved_references", reference_count if reference_count else 0))

    leakage_count = 0
    for table in execution.get("tables", []):
        if table.get("collection_id") and table.get("collection_id") != internal_collection:
            leakage_count += 1
    for ref in references:
        if ref.get("collection_id") and ref.get("collection_id") != internal_collection:
            leakage_count += 1

    passed = (
        confidence >= min_confidence
        and unresolved_count <= max_unresolved
        and not missing_terms
        and leakage_count == 0
    )

    return {
        "question": question,
        "collection": collection,
        "confidence": confidence,
        "reference_count": reference_count,
        "unresolved_reference_count": unresolved_count,
        "term_coverage": 1.0 if not must_include_terms else (len(must_include_terms) - len(missing_terms)) / len(must_include_terms),
        "missing_terms": missing_terms,
        "scope_leakage_count": leakage_count,
        "passed": passed,
    }


def aggregate_metrics(scenario_metrics: list[dict]) -> dict:
    if not scenario_metrics:
        return {
            "scenario_count": 0,
            "pass_rate": 0.0,
            "average_confidence": 0.0,
            "unresolved_reference_rate": 0.0,
            "scope_leakage_count": 0,
        }

    scenario_count = len(scenario_metrics)
    passed = len([m for m in scenario_metrics if m["passed"]])
    total_refs = sum(m["reference_count"] for m in scenario_metrics)
    unresolved_refs = sum(m["unresolved_reference_count"] for m in scenario_metrics)
    avg_confidence = sum(m["confidence"] for m in scenario_metrics) / scenario_count
    leakage = sum(m["scope_leakage_count"] for m in scenario_metrics)
    unresolved_rate = (unresolved_refs / total_refs) if total_refs else 0.0

    return {
        "scenario_count": scenario_count,
        "pass_rate": round(passed / scenario_count, 4),
        "average_confidence": round(avg_confidence, 4),
        "unresolved_reference_rate": round(unresolved_rate, 4),
        "scope_leakage_count": leakage,
    }


def collection_metrics(scenario_metrics: list[dict]) -> dict:
    by_collection: dict[str, list[dict]] = {}
    for metric in scenario_metrics:
        by_collection.setdefault(metric["collection"], []).append(metric)
    return {collection: aggregate_metrics(metrics) for collection, metrics in by_collection.items()}


def evaluate_regression_status(aggregate: dict, thresholds: dict | None = None) -> dict:
    thresholds = thresholds or {}
    min_pass_rate = float(thresholds.get("min_pass_rate", 0.0))
    max_unresolved_rate = float(thresholds.get("max_unresolved_reference_rate", 1.0))
    min_avg_confidence = float(thresholds.get("min_average_confidence", 0.0))

    breaches = []
    if aggregate["pass_rate"] < min_pass_rate:
        breaches.append("min_pass_rate")
    if aggregate["unresolved_reference_rate"] > max_unresolved_rate:
        breaches.append("max_unresolved_reference_rate")
    if aggregate["average_confidence"] < min_avg_confidence:
        breaches.append("min_average_confidence")

    return {
        "passed": len(breaches) == 0,
        "breached_thresholds": breaches,
        "thresholds": {
            "min_pass_rate": min_pass_rate,
            "max_unresolved_reference_rate": max_unresolved_rate,
            "min_average_confidence": min_avg_confidence,
        },
    }
