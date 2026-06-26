from __future__ import annotations

from datetime import datetime
import re


def _section_distance(source: str | None, target: str | None) -> float:
    if not source or not target:
        return 9999.0
    source_parts = [int(part) for part in re.findall(r"\d+", source)]
    target_parts = [int(part) for part in re.findall(r"\d+", target)]
    if not source_parts or not target_parts:
        return 9999.0
    max_len = max(len(source_parts), len(target_parts))
    source_parts.extend([0] * (max_len - len(source_parts)))
    target_parts.extend([0] * (max_len - len(target_parts)))
    weighted = 0.0
    for idx, (left, right) in enumerate(zip(source_parts, target_parts), start=1):
        weighted += abs(left - right) / (10 ** (idx - 1))
    return weighted


def _timestamp_score(timestamp: str | None) -> float:
    if not timestamp:
        return 0.0
    try:
        return datetime.fromisoformat(timestamp).timestamp()
    except ValueError:
        return 0.0


def disambiguate(candidates: list[dict], context: dict) -> list[dict]:
    source_document_id = context.get("source_document_id")
    source_section_label = context.get("source_section_label")

    ranked = []
    for candidate in candidates:
        same_doc = 1 if candidate.get("document_id") == source_document_id else 0
        distance = _section_distance(source_section_label, candidate.get("section_label"))
        timestamp = _timestamp_score(candidate.get("timestamp"))
        confidence = float(candidate.get("confidence", 0.0))
        ranked.append(
            {
                **candidate,
                "_score_tuple": (
                    same_doc,
                    -distance,
                    timestamp,
                    confidence,
                    candidate.get("chunk_id", ""),
                ),
            }
        )

    ranked.sort(key=lambda item: item["_score_tuple"], reverse=True)
    for item in ranked:
        item.pop("_score_tuple", None)
    return ranked
