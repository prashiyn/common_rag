"""External collection symbols vs internal Neo4j ids: internal ids use prefix ``tgt_graph_<external>``."""

from __future__ import annotations

from typing import Any

INTERNAL_PREFIX = "tgt_graph_"

_COLLECTION_VALUE_KEYS = frozenset({"collection", "collection_id"})


def _strip_prefix_case_insensitive(s: str) -> str:
    plen = len(INTERNAL_PREFIX)
    if len(s) >= plen and s[:plen].lower() == INTERNAL_PREFIX.lower():
        return s[plen:]
    return s


def to_internal(name: str | None) -> str | None:
    """Map an external collection id to the internal graph id (idempotent)."""
    if name is None:
        return None
    s = name.strip()
    if not s:
        return name
    base = _strip_prefix_case_insensitive(s)
    return INTERNAL_PREFIX + base


def to_external(name: str | None) -> str | None:
    """Strip internal prefix for client-visible collection ids."""
    if name is None:
        return None
    s = name.strip()
    return _strip_prefix_case_insensitive(s)


def transform_inbound_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: (
                to_internal(v)
                if k in _COLLECTION_VALUE_KEYS and isinstance(v, str) and v.strip()
                else transform_inbound_payload(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [transform_inbound_payload(i) for i in obj]
    return obj


def _maybe_strip_prefixed_id_or_name(v: Any) -> Any:
    if isinstance(v, str) and len(v) >= len(INTERNAL_PREFIX) and v[: len(INTERNAL_PREFIX)].lower() == INTERNAL_PREFIX.lower():
        return to_external(v)
    return v


def transform_outbound_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in _COLLECTION_VALUE_KEYS:
                out[k] = to_external(v) if isinstance(v, str) else transform_outbound_payload(v)
            elif k in ("id", "name") and isinstance(v, str):
                out[k] = _maybe_strip_prefixed_id_or_name(v)
            else:
                out[k] = transform_outbound_payload(v)
        return out
    if isinstance(obj, list):
        return [transform_outbound_payload(i) for i in obj]
    return obj


def rewrite_collections_path(path: str) -> str | None:
    """Return rewritten path for ``/collections/<id>`` or None if unchanged."""
    if not path.startswith("/collections/"):
        return None
    rest = path.removeprefix("/collections/").strip("/")
    if not rest or "/" in rest:
        return None
    if rest == "get-or-create":
        return None
    internal = to_internal(rest)
    if internal == rest:
        return None
    return f"/collections/{internal}"
