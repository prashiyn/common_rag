"""Unified OpenAPI export contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED_API_ROOT = REPO_ROOT / "unified_api"
OPENAPI_DIR = REPO_ROOT / "docs" / "openapi"
EXPORT_SCRIPT = UNIFIED_API_ROOT / "scripts" / "export_openapi.py"

EXPECTED_SLICES = (
    "llm-service",
    "doc-processing",
    "core-rag",
    "ra-literag",
    "temporal-graph",
    "temporal-graph-openai",
    "temporal-graph-traversal",
)


@pytest.fixture(scope="module")
def unified_spec() -> dict:
    if str(UNIFIED_API_ROOT) not in sys.path:
        sys.path.insert(0, str(UNIFIED_API_ROOT))
    from unified_api.main import app

    return app.openapi()


def test_unified_spec_has_expected_route_prefixes(unified_spec: dict) -> None:
    paths = set(unified_spec.get("paths", {}))
    assert "/health" in paths
    assert any(p.startswith("/llm-service/") for p in paths)
    assert any(p.startswith("/doc-processing/") for p in paths)
    assert any(p.startswith("/core-rag/") for p in paths)
    assert any(p.startswith("/ra-literag/") for p in paths)
    assert any(p.startswith("/temporal-graph/") for p in paths)
    assert any(p.startswith("/temporal-graph-openai/") for p in paths)
    assert any(p.startswith("/temporal-graph-traversal/") for p in paths)
    assert len(paths) >= 80


def test_frozen_unified_openapi_matches_export() -> None:
    for name in ("openapi.json", "unified-api.json"):
        spec_path = OPENAPI_DIR / name
        assert spec_path.exists(), "Run: cd unified_api && uv run python scripts/export_openapi.py"

        exported = json.loads(spec_path.read_text(encoding="utf-8"))
        assert exported["info"]["title"] == "Unified API"
        assert exported.get("servers"), "exported spec should include servers block"
        assert len(exported.get("paths", {})) >= 80

    canonical = json.loads((OPENAPI_DIR / "openapi.json").read_text(encoding="utf-8"))
    alias = json.loads((OPENAPI_DIR / "unified-api.json").read_text(encoding="utf-8"))
    assert canonical == alias


@pytest.mark.parametrize("slice_name", EXPECTED_SLICES)
def test_by_service_slice_exists(slice_name: str) -> None:
    slice_path = OPENAPI_DIR / "by-service" / f"{slice_name}.json"
    assert slice_path.exists(), f"Missing slice: {slice_path}"
    data = json.loads(slice_path.read_text(encoding="utf-8"))
    assert data["paths"], f"Slice {slice_name} has no paths"


def test_export_openapi_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--check"],
        cwd=UNIFIED_API_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
