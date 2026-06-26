#!/usr/bin/env python3
"""
Generate OpenAPI 3.0 spec for the RAG-Anything API and write to docs/.

Usage (from repo root):
  uv run python scripts/generate_openapi.py

Output:
  docs/openapi.json  - full OpenAPI 3.0 schema
  docs/openapi.yaml  - same schema in YAML (for import into other tools)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app

DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)


def main() -> None:
    schema = app.openapi()
    out_json = DOCS_DIR / "openapi.json"
    out_yaml = DOCS_DIR / "openapi.yaml"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_json}")

    try:
        import yaml
        with open(out_yaml, "w", encoding="utf-8") as f:
            yaml.dump(schema, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"Wrote {out_yaml}")
    except ImportError:
        print("Install pyyaml (uv sync --extra server) to emit openapi.yaml")


if __name__ == "__main__":
    main()
