#!/usr/bin/env python3
"""
Copy database credentials from the repo-root `.env` into each service's `.env`.

Extend by appending to SERVICE_NAMES only; Postgres database names map from root keys
`POSTGRES_DB_<SERVICENAME>` (SERVICENAME is the folder in upper case, e.g. fin_rag -> POSTGRES_DB_FIN_RAG).

Usage:
  python scripts/sync_service_env_from_root.py
  python scripts/sync_service_env_from_root.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

# --- extend this list when you add a service with a service/.env file ------------
SERVICE_NAMES: tuple[str, ...] = (
    "core_rag_graph",
    "fin_rag",
    "ra_literag",
    "temporial_graph",
    "temporial_graph_openai",
    "temporial_graph_traversal",
)
# ----------------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_ENV = REPO_ROOT / ".env"

ASSIGN_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_root_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        out[k] = v
    return out


def require_root_keys(root: dict[str, str]) -> dict[str, str]:
    needed = (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
    )
    missing = [k for k in needed if not root.get(k)]
    if missing:
        print(
            f"error: root env is missing required keys: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return root


def postgres_db_root_key(service_dir: str) -> str:
    return f"POSTGRES_DB_{service_dir.upper()}"


def postgres_db_for_service(service_dir: str, root: dict[str, str]) -> str | None:
    """
    Resolve logical database name for a service directory, or None if this service
    does not use postgres in the unified stack.
    """
    key = postgres_db_root_key(service_dir)
    val = (root.get(key) or "").strip()
    if val:
        return val
    defaults = {
        "fin_rag": "fin_rag",
        "ra_literag": "ra_literag",
    }
    return defaults.get(service_dir)


def fmt_env_val(value: str) -> str:
    if any(ch in value for ch in ' \t\n#"\'\\'):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def rewrite_database_url(url: str, user: str, password: str, database: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("postgresql", "postgres"):
        return url
    host = p.hostname or "localhost"
    port = p.port
    netloc_body = host
    if port is not None:
        netloc_body = f"{host}:{port}"
    u = quote(user, safe="")
    pw = quote(password, safe="")
    netloc = f"{u}:{pw}@{netloc_body}"
    db = database.lstrip("/")
    path = f"/{db}" if db else "/"
    return urlunparse((p.scheme, netloc, path, "", "", ""))


def build_substitutions(service_dir: str, root: dict[str, str]) -> dict[str, str]:
    pu = root["POSTGRES_USER"]
    pp = root["POSTGRES_PASSWORD"]
    nu, np = root["NEO4J_USERNAME"], root["NEO4J_PASSWORD"]

    subs: dict[str, str] = {
        "POSTGRES_USER": pu,
        "POSTGRES_PASSWORD": pp,
        "NEO4J_USERNAME": nu,
        "NEO4J_USER": nu,
        "NEO4J_PASSWORD": np,
    }

    pdb = postgres_db_for_service(service_dir, root)
    if pdb:
        subs["POSTGRES_DATABASE"] = pdb

    return subs


def sync_file(
    svc_path: Path,
    substitutions: dict[str, str],
    *,
    dry_run: bool,
) -> list[str]:
    text = svc_path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    changed: list[str] = []

    for line in text.splitlines(keepends=False):
        m = ASSIGN_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        indent, key, _old_tail = m.group(1), m.group(2), m.group(3)
        if key == "DATABASE_URL":
            if "POSTGRES_DATABASE" not in substitutions:
                out_lines.append(line)
                continue
            old_url = m.group(3).strip().strip('"').strip("'")
            pu = substitutions["POSTGRES_USER"]
            pp = substitutions["POSTGRES_PASSWORD"]
            pdb = substitutions["POSTGRES_DATABASE"]
            new_url = rewrite_database_url(old_url, pu, pp, pdb)
            if new_url != old_url:
                changed.append(f"  DATABASE_URL ({svc_path.relative_to(REPO_ROOT)})")
            newline = f"{indent}DATABASE_URL={fmt_env_val(new_url)}"
            out_lines.append(newline)
            continue

        if key in substitutions:
            new_val = substitutions[key]
            old_val_full = m.group(3).rstrip("\n")
            old_val = old_val_full.strip().strip('"').strip("'")
            if old_val != new_val:
                changed.append(f"  {key} ({svc_path.relative_to(REPO_ROOT)})")
            newline = f"{indent}{key}={fmt_env_val(new_val)}"
            out_lines.append(newline)
            continue

        out_lines.append(line)

    out_text = "\n".join(out_lines)
    if text.endswith("\n") or not text:
        out_text += "\n"

    if not dry_run and changed:
        svc_path.write_text(out_text, encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Align Postgres/Neo4j credentials in service .env files from repo-root .env."
    )
    ap.add_argument(
        "--root-env",
        type=Path,
        default=ROOT_ENV,
        help=f"path to root .env (default: {ROOT_ENV})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would change without writing files",
    )
    args = ap.parse_args()

    if not args.root_env.is_file():
        print(
            f"error: root env file not found: {args.root_env}\n"
            f"  Copy {args.root_env.with_name('.env.example')} to .env and set values.",
            file=sys.stderr,
        )
        return 1

    root = require_root_keys(parse_root_env(args.root_env))

    all_changed: list[str] = []
    for name in SERVICE_NAMES:
        svc_env = REPO_ROOT / name / ".env"
        if not svc_env.is_file():
            print(f"skip: no file {svc_env.relative_to(REPO_ROOT)}", file=sys.stderr)
            continue
        subs = build_substitutions(name, root)
        changed = sync_file(svc_env, subs, dry_run=args.dry_run)
        all_changed.extend(changed)

    if args.dry_run:
        if all_changed:
            print("Would update:")
            for c in all_changed:
                print(c)
        else:
            print("No changes needed (dry-run).")
    else:
        if all_changed:
            print("Updated:")
            for c in all_changed:
                print(c)
        else:
            print("No changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
