from __future__ import annotations

import re

from raqe.collection_namespace import to_internal
from raqe.models.reference_resolution import ReferenceCandidate, ResolvedReference
from raqe.structure.disambiguator import disambiguate

LABEL_PATTERN = re.compile(r"([A-Za-z]*\s*)?([0-9]+(?:\.[0-9]+)?)")


def normalize_reference_label(reference_text: str, target_label: str | None) -> str:
    if target_label:
        return target_label.strip().lower()
    match = LABEL_PATTERN.search(reference_text or "")
    if not match:
        return ""
    return match.group(2).strip().lower()


def _candidate_label(candidate: dict) -> str:
    section_label = candidate.get("section_label")
    if section_label:
        return str(section_label).strip().lower()
    return normalize_reference_label(candidate.get("content", ""), None)


def resolve_reference(
    ref: dict,
    collection: str,
    doc_ids: list[str],
    source_chunk: dict,
    candidates: list[dict],
) -> dict:
    if not collection:
        raise ValueError("collection is required")
    collection = to_internal(collection) or collection
    if not doc_ids:
        result = ResolvedReference(
            source_chunk_id=source_chunk["chunk_id"],
            source_document_id=source_chunk["document_id"],
            collection_id=collection,
            reference_text=ref.get("reference_text", ""),
            reference_type=ref.get("reference_type", "OTHER"),
            target_label=normalize_reference_label(ref.get("reference_text", ""), ref.get("target_label")),
            resolved=False,
            reason="no scoped documents",
        )
        return result.model_dump()

    normalized_label = normalize_reference_label(ref.get("reference_text", ""), ref.get("target_label"))
    scoped = []
    allowed_doc_ids = set(doc_ids)
    for candidate in candidates:
        if candidate.get("collection_id") != collection:
            continue
        if candidate.get("document_id") not in allowed_doc_ids:
            continue
        if normalized_label and _candidate_label(candidate) != normalized_label:
            continue
        scoped.append(
            ReferenceCandidate(
                collection_id=candidate["collection_id"],
                document_id=candidate["document_id"],
                chunk_id=candidate["chunk_id"],
                section_label=candidate.get("section_label"),
                timestamp=candidate.get("timestamp", ""),
                confidence=float(ref.get("confidence", 0.0)),
            ).model_dump()
        )

    if not scoped:
        result = ResolvedReference(
            source_chunk_id=source_chunk["chunk_id"],
            source_document_id=source_chunk["document_id"],
            collection_id=collection,
            reference_text=ref.get("reference_text", ""),
            reference_type=ref.get("reference_type", "OTHER"),
            target_label=normalized_label,
            resolved=False,
            reason="no candidates in scoped collection/documents",
        )
        return result.model_dump()

    ranked = disambiguate(
        scoped,
        context={
            "source_document_id": source_chunk["document_id"],
            "source_section_label": source_chunk.get("section_label"),
        },
    )
    selected = ranked[0]
    result = ResolvedReference(
        source_chunk_id=source_chunk["chunk_id"],
        source_document_id=source_chunk["document_id"],
        collection_id=collection,
        reference_text=ref.get("reference_text", ""),
        reference_type=ref.get("reference_type", "OTHER"),
        target_label=normalized_label,
        resolved=True,
        target_chunk_id=selected["chunk_id"],
        target_document_id=selected["document_id"],
        target_section_label=selected.get("section_label"),
        score=selected.get("confidence", 0.0),
        reason="resolved via disambiguation ranking",
        ranked_candidates=ranked,
    )
    return result.model_dump()


def resolve_structure_references(
    collection: str,
    doc_ids: list[str],
    filtered_chunks: list[dict],
) -> list[dict]:
    candidates = filtered_chunks
    resolved_entries: list[dict] = []
    for chunk in filtered_chunks:
        references = chunk.get("references", [])
        for ref in references:
            resolved_entries.append(
                resolve_reference(
                    ref=ref,
                    collection=collection,
                    doc_ids=doc_ids,
                    source_chunk=chunk,
                    candidates=candidates,
                )
            )
    return resolved_entries
