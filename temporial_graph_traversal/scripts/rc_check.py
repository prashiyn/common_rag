from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from raqe.backtesting import run_backtest_scenarios
from raqe.main import app


def run_rc_checks() -> dict:
    client = TestClient(app)
    report: dict = {"gates": {}}

    def capture(name: str, fn):
        try:
            report["gates"][name] = fn()
        except Exception as exc:  # noqa: BLE001
            report["gates"][name] = {"ok": False, "error": str(exc)}

    capture(
        "health",
        lambda: (
            lambda r: {"ok": r.status_code == 200 and r.json().get("status") == "ok", "status_code": r.status_code}
        )(client.get("/health")),
    )
    capture(
        "collections_list",
        lambda: (lambda r: {"ok": r.status_code == 200, "status_code": r.status_code})(client.get("/collections")),
    )
    capture(
        "collections_get_or_create",
        lambda: (
            lambda r: {"ok": r.status_code == 200, "status_code": r.status_code}
        )(client.post("/collections/get-or-create", json={"collection_id": "RC_CHECK"})),
    )
    capture(
        "query_ask",
        lambda: (
            lambda r: {"ok": r.status_code in (200, 404, 422), "status_code": r.status_code}
        )(
            client.post(
                "/query/ask",
                json={"question": "Why did revenue change for RELIANCE in Q1 FY24?", "collection": "RELIANCE"},
            )
        ),
    )

    scenarios = [
        {
            "id": "rc-001",
            "question": "Why did revenue increase in Q1 FY24 for RELIANCE?",
            "collection": "RELIANCE",
            "expected": {
                "min_confidence": 0.4,
                "must_include_terms": ["revenue"],
                "max_unresolved_references": 1,
            },
        }
    ]
    thresholds = {
        "min_pass_rate": 0.8,
        "max_unresolved_reference_rate": 0.2,
        "min_average_confidence": 0.4,
    }
    capture(
        "backtesting",
        lambda: (
            lambda r: {
                "ok": r["regression_status"]["passed"],
                "run_summary": r["run_summary"],
                "regression_status": r["regression_status"],
            }
        )(run_backtest_scenarios(scenarios, thresholds=thresholds)),
    )

    gate_values = list(report["gates"].values())
    report["overall_pass"] = all(gate.get("ok") for gate in gate_values)
    return report


if __name__ == "__main__":
    result = run_rc_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nRC_CHECK: {'PASS' if result['overall_pass'] else 'FAIL'}")
    sys.exit(0 if result["overall_pass"] else 1)
