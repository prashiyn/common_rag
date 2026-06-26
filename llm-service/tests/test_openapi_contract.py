from __future__ import annotations

import json
from pathlib import Path

from llm_service.main import create_app


def test_openapi_contract_matches_snapshot() -> None:
    current = create_app().openapi()
    snapshot_path = Path(__file__).resolve().parents[1] / "openapi.snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert current == snapshot
