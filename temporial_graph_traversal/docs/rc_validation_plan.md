# RC Validation Plan (Runnable)

## Goal

Validate the release candidate end-to-end before freeze using deterministic checks for API contract, pipeline correctness, and backtesting thresholds.

---

## Prerequisites

- `uv` installed
- project dependencies synced
- optional Neo4j running for live graph checks

Run:

```bash
uv sync
```

---

## 1) Static Quality Gate

Run full test suite:

```bash
uv run pytest
```

Expected:

- all tests pass
- no flaky failures on repeated run

---

## 2) API Contract Gate

Validate core endpoints:

- `GET /health`
- `GET /collections`
- `GET /collections/{collection_id}`
- `POST /collections/get-or-create`
- `POST /query/ask`

Smoke run:

```bash
uv run uvicorn raqe.main:app --host 0.0.0.0 --port 8000
```

Then verify:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/collections
curl -s -X POST http://localhost:8000/collections/get-or-create -H "Content-Type: application/json" -d '{"collection_id":"RELIANCE"}'
curl -s -X POST http://localhost:8000/query/ask -H "Content-Type: application/json" -d '{"question":"Why did revenue change for RELIANCE in Q1 FY24?"}'
```

Expected:

- typed JSON responses
- deterministic error codes for invalid requests

---

## 3) Scope Safety Gate

Validate no cross-collection leakage:

1. Seed at least 2 collections (`RELIANCE`, `INFY`) with overlapping labels.
2. Run collection-scoped query for one collection.
3. Confirm returned references/tables/events contain only requested collection.

Pass criteria:

- leakage count = 0 in execution/backtesting metrics

---

## 4) Strict/Non-Strict Reference Resolution Gate

Verify unresolved reference behavior:

- non-strict mode (default): query returns `200` with unresolved traces
- strict mode (`strict_reference_resolution=true`): query returns `422 unresolved_reference`

---

## 5) OpenAPI Gate

Source of truth file:

- `docs/project_openapi.json`

Regenerate before final freeze:

```bash
uv run python -c "import json; from raqe.main import app; from pathlib import Path; p=Path('docs/project_openapi.json'); p.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True))"
```

Pass criteria:

- file reflects latest routes/models and is committed with RC changes

---

## 6) Backtesting Gate

Run scenario replay with thresholds:

```python
from raqe.backtesting import run_backtest_scenarios

scenarios = [
    {
        "id": "rc-001",
        "question": "Why did revenue increase in Q1 FY24 for RELIANCE?",
        "collection": "RELIANCE",
        "expected": {
            "min_confidence": 0.4,
            "must_include_terms": ["revenue"],
            "max_unresolved_references": 1
        }
    }
]

thresholds = {
    "min_pass_rate": 0.8,
    "max_unresolved_reference_rate": 0.2,
    "min_average_confidence": 0.4
}

report = run_backtest_scenarios(scenarios, thresholds=thresholds)
print(report["regression_status"])
```

Pass criteria:

- `regression_status.passed == true`
- no threshold breaches

---

## 7) Freeze Checklist

- [ ] Full test suite passed (`uv run pytest`)
- [ ] API smoke checks passed
- [ ] Scope leakage checks passed
- [ ] Strict/non-strict reference behavior verified
- [ ] `docs/project_openapi.json` regenerated and up to date
- [ ] Backtesting thresholds passed
- [ ] RC report archived with timestamp and git SHA
