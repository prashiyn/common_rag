# Backtesting Protocol

## Purpose

This protocol defines how to run and interpret RAQE backtesting runs.

## Scenario Schema

Each scenario must include:

- `id`
- `question`
- `collection`
- `expected` (optional thresholds for scenario-level checks)

Example:

```json
{
  "id": "case-001",
  "question": "Why did revenue increase in Q1 FY24 for RELIANCE?",
  "collection": "RELIANCE",
  "expected": {
    "min_confidence": 0.4,
    "must_include_terms": ["revenue", "q1"],
    "max_unresolved_references": 0
  }
}
```

## Run Backtest

Use `run_backtest_scenarios` from `raqe.backtesting`.

High-level flow:

1. Validate scenarios
2. Replay each scenario via `run_query`
3. Compute scenario metrics
4. Compute aggregate + per-collection metrics
5. Evaluate regression thresholds

## Thresholds

Supported thresholds:

- `min_pass_rate`
- `max_unresolved_reference_rate`
- `min_average_confidence`

## Output Interpretation

- `run_summary`: overall execution status
- `aggregate_metrics`: global quality indicators
- `collection_metrics`: grouped indicators by collection
- `scenario_results`: detailed scenario-level outcomes
- `regression_status`: pass/fail and breached thresholds

## Failure Handling

- Scenario errors are captured per scenario and do not stop the full run.
- Input validation errors (missing id/question/collection) stop execution early.
