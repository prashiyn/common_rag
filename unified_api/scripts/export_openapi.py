#!/usr/bin/env python3
"""Export unified OpenAPI specs for integrators and downstream services.

Generates:
  docs/openapi/openapi.json            — canonical full unified API (all route prefixes)
  docs/openapi/openapi.yaml
  docs/openapi/unified-api.json        — same content as openapi.json (alias)
  docs/openapi/unified-api.yaml
  docs/openapi/by-service/<name>.json  — per-prefix slices for consumers
  docs/openapi/by-service/<name>.yaml

Usage (from unified_api/):
  uv run python scripts/export_openapi.py
  uv run python scripts/export_openapi.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
UNIFIED_API_ROOT = SCRIPT_DIR.parent
REPO_ROOT = UNIFIED_API_ROOT.parent
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "openapi"
BY_SERVICE_DIR = DEFAULT_OUT_DIR / "by-service"

# Longest prefixes first so /temporal-graph-openai is not captured by /temporal-graph.
SERVICE_SLICES: tuple[tuple[str, str], ...] = (
    ("temporal-graph-traversal", "/temporal-graph-traversal"),
    ("temporal-graph-openai", "/temporal-graph-openai"),
    ("temporal-graph", "/temporal-graph"),
    ("llm-service", "/llm-service"),
    ("doc-processing", "/doc-processing"),
    ("core-rag", "/core-rag"),
    ("ra-literag", "/ra-literag"),
)

DEFAULT_SERVERS: list[dict[str, str]] = [
    {"url": "http://127.0.0.1:8000", "description": "Local development"},
    {"url": "http://localhost:8000", "description": "Local development (localhost)"},
    {"url": "http://unified_api:8000", "description": "Docker Compose network"},
]


def _load_app():
    if str(UNIFIED_API_ROOT) not in sys.path:
        sys.path.insert(0, str(UNIFIED_API_ROOT))
    from unified_api.main import app

    return app


def _render_openapi() -> dict[str, Any]:
    app = _load_app()
    spec = app.openapi()
    spec = deepcopy(spec)
    spec["servers"] = DEFAULT_SERVERS
    return spec


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _dump_yaml(data: dict[str, Any]) -> str:
    import yaml

    return yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _slice_spec(full: dict[str, Any], name: str, prefix: str) -> dict[str, Any]:
    paths = {
        path: operations
        for path, operations in full.get("paths", {}).items()
        if _path_matches_prefix(path, prefix)
    }
    if not paths:
        raise ValueError(f"No paths matched prefix {prefix!r} for slice {name!r}")

    return {
        "openapi": full["openapi"],
        "info": {
            "title": f"Unified API — {name}",
            "description": (
                f"OpenAPI slice for `{prefix}` routes on the unified API. "
                "Generated from unified_api; use openapi.json for the full contract."
            ),
            "version": full["info"]["version"],
        },
        "servers": full.get("servers", []),
        "paths": paths,
        "components": deepcopy(full.get("components", {})),
    }


def _write_full_spec(out_dir: Path, full: dict[str, Any]) -> list[Path]:
    """Write complete unified spec under canonical and alias filenames."""
    written: list[Path] = []
    payload_json = _dump_json(full)
    payload_yaml = _dump_yaml(full)
    for stem in ("openapi", "unified-api"):
        json_path = out_dir / f"{stem}.json"
        json_path.write_text(payload_json, encoding="utf-8")
        written.append(json_path)
        yaml_path = out_dir / f"{stem}.yaml"
        yaml_path.write_text(payload_yaml, encoding="utf-8")
        written.append(yaml_path)
    return written


def _write_outputs(out_dir: Path, full: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    BY_SERVICE_DIR.mkdir(parents=True, exist_ok=True)

    written.extend(_write_full_spec(out_dir, full))

    for name, prefix in SERVICE_SLICES:
        sliced = _slice_spec(full, name, prefix)
        slice_json = BY_SERVICE_DIR / f"{name}.json"
        slice_json.write_text(_dump_json(sliced), encoding="utf-8")
        written.append(slice_json)

        slice_yaml = BY_SERVICE_DIR / f"{name}.yaml"
        slice_yaml.write_text(_dump_yaml(sliced), encoding="utf-8")
        written.append(slice_yaml)

    return written


def _check_outputs(out_dir: Path, full: dict[str, Any]) -> int:
    expected_files: dict[Path, dict[str, Any]] = {
        out_dir / "openapi.json": full,
        out_dir / "unified-api.json": full,
    }
    for name, prefix in SERVICE_SLICES:
        expected_files[out_dir / "by-service" / f"{name}.json"] = _slice_spec(
            full, name, prefix
        )

    exit_code = 0
    for path, expected in expected_files.items():
        if not path.exists():
            print(f"OpenAPI file missing: {path}")
            exit_code = 1
            continue
        current = json.loads(path.read_text(encoding="utf-8"))
        if current != expected:
            print(f"OpenAPI file is out of date: {path}")
            exit_code = 1

    if exit_code:
        print("Run: cd unified_api && uv run python scripts/export_openapi.py")
    else:
        print(f"OpenAPI exports are up to date under {out_dir}")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Export unified API OpenAPI specifications.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if exported JSON files are stale.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args()

    full = _render_openapi()

    if args.check:
        return _check_outputs(args.output_dir, full)

    written = _write_outputs(args.output_dir, full)
    path_count = len(full.get("paths", {}))
    print(f"Exported unified OpenAPI ({path_count} paths):")
    for path in written:
        print(f"  {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
