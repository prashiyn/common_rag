# Phase 9 Comprehensive Implementation Guide

## RAQE Phase 9 - Backtesting + Signal Validation

This document is the execution guide for Phase 9 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 9 Objective

Build a repeatable backtesting and validation layer that replays historical queries against collections/documents and scores output quality and stability.

Phase 9 must guarantee:

1. Replays are deterministic and reproducible.
2. Validation reports are structured and machine-readable.
3. Metrics capture answer quality + reference correctness + stability.
4. Results are grouped by collection with leakage checks.

---

## 2) Inputs and Dependencies

Phase 9 depends on:

- Phase 1-7 functional query pipeline (`run_query`)
- Structured result contract (`QueryResult`)
- Existing test harness and deterministic mocks

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`

---

## 3) Scope Boundaries

Included:

- Backtesting dataset schemas
- Replay runner
- Validation metrics computation
- Protocol document for how to run and interpret reports
- Unit/integration tests for regressions

Not included:

- External dashboards
- CI publishing/report upload

---

## 4) Target File Plan

Create/update these files:

- `app/backtesting/metrics.py` (create)
- `app/backtesting/replay_runner.py` (create)
- `app/backtesting/__init__.py` (create)
- `tests/backtesting/test_replay_regressions.py` (create)
- `docs/backtesting_protocol.md` (create)

---

## 5) Functional Requirements

## 5.1 Dataset Contract

Replay runner input should accept a list of scenarios:

```json
[
  {
    "id": "case-001",
    "question": "Why did revenue increase in Q1 FY24 for RELIANCE?",
    "collection": "RELIANCE",
    "expected": {
      "min_confidence": 0.4,
      "must_include_terms": ["revenue", "Q1"],
      "max_unresolved_references": 0
    }
  }
]
```

## 5.2 Replay Runner

Implement:

- `run_backtest_scenarios(scenarios, query_runner=run_query) -> dict`
- executes each scenario
- captures success/failure payloads
- computes per-scenario and aggregate metrics
- groups metrics by collection

## 5.3 Metrics

Implement:

- accuracy proxy from required terms
- confidence distribution
- unresolved reference rate
- document scope leakage count (references/tables from wrong collection)
- overall pass rate

## 5.4 Regression Thresholds

Support thresholds in runner:

- `min_pass_rate`
- `max_unresolved_reference_rate`
- `min_average_confidence`

Return explicit pass/fail status and breached thresholds.

---

## 6) Output Contract

Backtesting result payload should include:

- `run_summary`
- `aggregate_metrics`
- `collection_metrics`
- `scenario_results`
- `regression_status`

Each scenario result should include:

- scenario id
- question/collection
- execution status
- measured metrics
- failures/reasons

---

## 7) Error Handling Rules

- scenario exceptions should not abort full run; capture per-scenario failure
- malformed scenario input should raise `ValueError` before execution
- missing question or collection in scenario should be explicit validation error

---

## 8) Test Plan (Comprehensive)

## 8.1 Backtesting unit/regression tests

1. Valid replay computes aggregate and per-collection metrics.
2. Term matching + unresolved reference scoring works.
3. Exceptions in one scenario do not stop remaining scenarios.
4. Regression thresholds produce correct pass/fail outcome.
5. Leakage detection flags cross-collection outputs.

---

## 9) Cursor Agent Execution Packets

### Packet A - Metrics Engine

```text
Task: Implement scenario and aggregate metric computation
Files: app/backtesting/metrics.py
Must preserve:
- deterministic scoring
- explicit leakage checks
Done when:
- metric-focused tests pass
```

### Packet B - Replay Runner

```text
Task: Implement scenario replay orchestration and regression status
Files: app/backtesting/replay_runner.py
Must preserve:
- continue-on-error behavior
- threshold evaluation
Done when:
- replay regression tests pass
```

### Packet C - Protocol

```text
Task: Write operator protocol for running and interpreting backtests
Files: docs/backtesting_protocol.md
Must preserve:
- clear run steps
- report interpretation guidelines
Done when:
- protocol is actionable and consistent with implementation
```

---

## 10) Phase 9 Definition of Done

Phase 9 is complete only when:

1. Backtest runner executes scenario sets end-to-end.
2. Aggregate + collection metrics are produced deterministically.
3. Regression thresholds are evaluated and reported.
4. Failures are isolated per scenario without aborting entire run.
5. Tests validate correctness, stability, and leakage detection.
