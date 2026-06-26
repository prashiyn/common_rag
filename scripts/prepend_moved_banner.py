#!/usr/bin/env python3
"""Prepend monorepo deprecation banner to in-tree service README.md files."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MOVED_MARKER = "# Moved"
COMMON_RAG_URL = "https://github.com/prashiyn/common_rag"

SERVICES: list[tuple[str, str]] = [
    ("llm-service/README.md", "llm-service/"),
    ("doc_processing/README.md", "doc_processing/"),
    ("core_rag_graph/README.md", "core_rag_graph/"),
    ("ra_literag/README.md", "ra_literag/"),
    ("temporial_graph/README.md", "temporial_graph/"),
    ("temporial_graph_openai/README.md", "temporial_graph_openai/"),
    ("temporial_graph_traversal/README.md", "temporial_graph_traversal/"),
    ("fin_rag/README.md", "fin_rag/"),
]


def banner(service_path: str) -> str:
    return (
        f"# Moved\n\n"
        f"This service now lives in the [common_rag]({COMMON_RAG_URL}) "
        f"monorepo under `{service_path}`.\n"
    )


def prepend(readme: Path, service_path: str) -> bool:
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if MOVED_MARKER in text:
        return False

    body = banner(service_path)
    if text.strip():
        body += "\n---\n\n" + text.lstrip("\n")
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(body, encoding="utf-8")
    return True


def main() -> None:
    changed = 0
    for rel, service_path in SERVICES:
        readme = REPO_ROOT / rel
        if prepend(readme, service_path):
            print(f"updated {rel}")
            changed += 1
        else:
            print(f"skip {rel} (banner already present)")
    print(f"done ({changed} updated)")


if __name__ == "__main__":
    main()
