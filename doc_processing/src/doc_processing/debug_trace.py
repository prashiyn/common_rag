"""
Debug tracing for document processing.

Enable with ``DEBUG=true`` in the environment (or ``.env``). Legacy alias:
``DOC_PROCESSING_DEBUG=DEBUG`` (still supported).

When enabled:

- FastAPI runs with ``debug=True`` (see ``main.create_app``).
- ``debug_print`` / debug logging emit diagnostic messages.
- Processing endpoints write artifacts under ``{temp_dir}/debug/``.
- The FFP pipeline writes per-step JSON (and markdown) under ``ffp/`` in that run folder.
"""

from __future__ import annotations

import json
import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from doc_processing.config import get_settings

logger = logging.getLogger(__name__)

_DEBUG_VALUE = "DEBUG"
_SAFE_SEGMENT = re.compile(r"[^a-zA-Z0-9._-]+")
_active_debug_run_dir: ContextVar[Path | None] = ContextVar("active_debug_run_dir", default=None)


def is_debug_enabled() -> bool:
    """
    True when ``DEBUG=true`` or legacy ``DOC_PROCESSING_DEBUG=DEBUG``.

    Single switch for FastAPI debug mode, artifact dumps, and ``debug_print``.
    """
    settings = get_settings()
    if settings.debug:
        return True
    raw = settings.doc_processing_debug
    if raw is None:
        return False
    return str(raw).strip().upper() == _DEBUG_VALUE


def configure_debug_logging() -> None:
    """Raise log verbosity for the app when debug mode is on."""
    if not is_debug_enabled():
        return
    root = logging.getLogger()
    if root.level > logging.DEBUG:
        root.setLevel(logging.DEBUG)
    logging.getLogger("doc_processing").setLevel(logging.DEBUG)
    print("[doc-processing debug] DEBUG enabled: verbose logging on", flush=True)


def debug_print(*args: object, sep: str = " ", end: str = "\n") -> None:
    """Print to stdout only when debug mode is enabled."""
    if is_debug_enabled():
        print("[doc-processing debug]", *args, sep=sep, end=end, flush=True)


def get_debug_base_dir() -> Path:
    """Root directory for debug artifacts (under configured temp dir)."""
    settings = get_settings()
    if settings.temp_dir:
        base = Path(settings.temp_dir).expanduser().resolve()
    else:
        base = (Path.cwd() / "data" / "temp").resolve()
    return base / "debug"


def _safe_segment(name: str, *, fallback: str = "run") -> str:
    cleaned = _SAFE_SEGMENT.sub("_", (name or "").strip())[:120]
    return cleaned or fallback


def bind_debug_run_dir(run_dir: Path | None) -> None:
    """Attach parser-level debug output to an endpoint run folder (optional)."""
    _active_debug_run_dir.set(run_dir)


@contextmanager
def debug_run_context(run_dir: Path | None) -> Iterator[Path | None]:
    """Bind *run_dir* for nested docling dumps for the duration of a request."""
    bind_debug_run_dir(run_dir)
    try:
        yield run_dir
    finally:
        bind_debug_run_dir(None)


def get_active_debug_run_dir() -> Path | None:
    return _active_debug_run_dir.get()


def resolve_docling_debug_dir(function_name: str) -> Path | None:
    """
    Directory for a docling parser function dump.

    Uses ``{active_run}/docling/{function}/`` when bound; otherwise
    ``{temp}/debug/docling/{function}/{timestamp}/``.
    """
    if not is_debug_enabled():
        return None
    parent = _active_debug_run_dir.get()
    fn = _safe_segment(function_name)
    try:
        if parent is not None:
            out = parent / "docling" / fn
            out.mkdir(parents=True, exist_ok=True)
            return out
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        out = get_debug_base_dir() / "docling" / fn / ts
        out.mkdir(parents=True, exist_ok=True)
        debug_print(f"docling debug dir: {out}")
        return out
    except OSError as e:
        logger.warning("Docling debug dir not created (%s): %s", function_name, e)
        return None


def create_debug_run_dir(endpoint: str, doc_id: str) -> Path | None:
    """
    Create ``{temp}/debug/{endpoint}/{doc_id}_{utc_timestamp}/``.

    Returns ``None`` when debug mode is off.
    """
    if not is_debug_enabled():
        return None
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        root = get_debug_base_dir() / _safe_segment(endpoint) / f"{_safe_segment(doc_id)}_{ts}"
        root.mkdir(parents=True, exist_ok=True)
        debug_print(f"debug run dir: {root}")
        return root
    except OSError as e:
        logger.warning("Debug run dir not created (%s/%s): %s", endpoint, doc_id, e)
        return None


def write_debug_bytes(run_dir: Path | None, relative_path: str, data: bytes) -> None:
    if run_dir is None:
        return
    path = run_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    debug_print(f"wrote {path} ({len(data)} bytes)")


def write_debug_text(run_dir: Path | None, relative_path: str, text: str) -> None:
    write_debug_bytes(run_dir, relative_path, (text or "").encode("utf-8"))


def write_debug_json(
    run_dir: Path | None,
    relative_path: str,
    payload: Any,
    *,
    default: Any = None,
) -> None:
    if run_dir is None:
        return
    try:
        body = json.dumps(payload, indent=2, ensure_ascii=False, default=default)
    except TypeError:
        body = json.dumps(str(payload), indent=2, ensure_ascii=False)
    write_debug_text(run_dir, relative_path, body)


def save_debug_original(
    run_dir: Path | None,
    source: bytes | Path,
    *,
    extension: str | None = None,
    filename: str = "original",
) -> None:
    """Persist the input file under ``original{extension}``."""
    if run_dir is None:
        return
    ext = extension or ""
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    rel = f"{filename}{ext}"
    if isinstance(source, bytes):
        write_debug_bytes(run_dir, rel, source)
        return
    path = Path(source)
    if path.is_file():
        write_debug_bytes(run_dir, rel, path.read_bytes())
    else:
        debug_print(f"skip original save; not a file: {path}")


def save_debug_markdown(run_dir: Path | None, markdown: str, *, filename: str = "converted.md") -> None:
    if run_dir is None:
        return
    write_debug_text(run_dir, filename, markdown or "")
