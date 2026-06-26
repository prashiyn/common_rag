import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _llm_paths(openapi: dict[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths") or {}
    return {k: v for k, v in paths.items() if k.startswith("/llm/")}


def test_llm_paths_not_exposed_by_doc_processing_openapi() -> None:
    """
    PR5 separation lock:
    doc-processing OpenAPI must not expose /llm paths anymore.
    """
    monolith_openapi = _load_json(Path(__file__).resolve().parents[2] / "openapi.json")
    mono_paths = _llm_paths(monolith_openapi)
    assert mono_paths == {}

def test_llm_service_openapi_still_exposes_llm_paths() -> None:
    """Standalone llm-service keeps /llm API ownership."""
    service_openapi = _load_json(Path(__file__).resolve().parents[1] / "openapi.json")
    service_paths = _llm_paths(service_openapi)
    assert set(service_paths.keys()) == {"/llm/complete", "/llm/models", "/llm/embeddings"}

