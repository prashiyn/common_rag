from __future__ import annotations

import re

from raqe.collection_namespace import to_internal
from raqe.agent.document_chunk_loader import load_document_chunks
from raqe.models.chunk_filtering import FilteredChunk


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_chunk(chunk: dict, target: str | None, section_hint: str | None) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    target_tokens = _tokenize(target)
    content_tokens = _tokenize(chunk.get("content", ""))
    title_tokens = _tokenize(chunk.get("title_summary", ""))
    section_tokens = _tokenize(chunk.get("section_title", ""))
    section_label_tokens = _tokenize(chunk.get("section_label", ""))

    if target_tokens and target_tokens.intersection(content_tokens):
        score += 3.0
        reasons.append("target_in_content")
    if target_tokens and target_tokens.intersection(title_tokens):
        score += 2.0
        reasons.append("target_in_title_summary")

    section_hint_tokens = _tokenize(section_hint)
    if section_hint_tokens and (
        section_hint_tokens.intersection(section_tokens)
        or section_hint_tokens.intersection(section_label_tokens)
    ):
        score += 1.5
        reasons.append("section_hint_match")

    references = chunk.get("references", [])
    if references:
        score += 1.0
        reasons.append("has_references")

    return score, reasons


def filter_chunks(
    collection: str,
    doc_ids: list[str],
    target: str | None = None,
    section_hint: str | None = None,
    driver=None,
) -> list[dict]:
    if not collection:
        raise ValueError("collection is required")
    collection = to_internal(collection) or collection
    if not doc_ids:
        return []

    chunks_by_doc = load_document_chunks(collection=collection, doc_ids=doc_ids, driver=driver)

    filtered: list[FilteredChunk] = []
    for document_id in doc_ids:
        for chunk in chunks_by_doc.get(document_id, []):
            score, reasons = _score_chunk(chunk, target=target, section_hint=section_hint)
            filtered.append(
                FilteredChunk(
                    collection_id=collection,
                    document_id=document_id,
                    chunk_id=chunk["chunk_id"],
                    content=chunk.get("content", ""),
                    title_summary=chunk.get("title_summary", ""),
                    section_title=chunk.get("section_title"),
                    section_label=chunk.get("section_label"),
                    timestamp=chunk.get("timestamp", ""),
                    references=chunk.get("references", []),
                    score=score,
                    match_reasons=reasons,
                )
            )

    filtered.sort(key=lambda item: (-item.score, item.timestamp, item.chunk_id), reverse=False)
    filtered.sort(key=lambda item: item.chunk_id)
    filtered.sort(key=lambda item: item.timestamp, reverse=True)
    filtered.sort(key=lambda item: item.score, reverse=True)
    return [item.model_dump() for item in filtered]
