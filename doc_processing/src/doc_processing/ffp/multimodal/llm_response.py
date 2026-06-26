"""Parse and validate LLM multimodal extraction responses (figures, tables)."""

from __future__ import annotations

import json
import re
from typing import Any

_MAX_SUMMARY_CHARS = 480

_SKIP_LITERALS = frozenset({"skip", "not_relevant", "n/a", "none", "irrelevant"})

# Prose patterns that indicate refusal, generic advice, or hallucination — discard.
_REJECTION_PHRASES = (
    "without specific data",
    "challenging to provide",
    "general approach to interpreting",
    "if you can provide more context",
    "appears to be a financial chart, but",
    "not feasible",
    "i can offer",
    "i could offer",
    "cannot provide a precise",
    "unable to analyze",
    "don't have access",
    "do not have access",
    "no visible data",
    "cannot see",
    "can't see",
    "hard to provide",
    "difficult to provide",
    "not possible to provide",
    "as an ai",
    "as a language model",
)


def strip_json_fence(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def _is_low_quality_prose(text: str) -> bool:
    lower = text.lower()
    if any(p in lower for p in _REJECTION_PHRASES):
        return True
    if len(re.findall(r"\d+\.\s+", text)) >= 3:
        return True
    if len(text) > _MAX_SUMMARY_CHARS and not re.search(r"\d", text):
        return True
    return False


def _coerce_relevant(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "1"):
            return True
        if v in ("false", "no", "0"):
            return False
    return None


def parse_relevance_response(raw: str, *, content_key: str = "text") -> str | None:
    """
    Parse strict JSON ``{"relevant": bool, "text": "..."}`` from the LLM.

    Returns summary text when relevant; ``None`` when the asset should be discarded.
    """
    cleaned = strip_json_fence(raw)
    if not cleaned:
        return None

    if cleaned.strip().lower() in _SKIP_LITERALS:
        return None

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_prose(cleaned)

    if not isinstance(data, dict):
        return _fallback_prose(cleaned)

    relevant = _coerce_relevant(data.get("relevant"))
    if relevant is False:
        return None
    if relevant is None:
        return None

    summary = data.get(content_key) or data.get("summary") or data.get("caption")
    if not isinstance(summary, str):
        return None

    summary = " ".join(summary.split())
    if not summary or _is_low_quality_prose(summary):
        return None
    if len(summary) > _MAX_SUMMARY_CHARS:
        summary = summary[:_MAX_SUMMARY_CHARS].rsplit(" ", 1)[0].strip()
    return summary or None


def _fallback_prose(text: str) -> str | None:
    """Use only when the model ignored JSON; reject ambiguous or verbose output."""
    compact = " ".join(text.split())
    if not compact or compact.lower() in _SKIP_LITERALS:
        return None
    if _is_low_quality_prose(compact):
        return None
    if len(compact) > _MAX_SUMMARY_CHARS:
        return None
    return compact
