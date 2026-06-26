from __future__ import annotations

import re
from datetime import datetime

from raqe.models.graph_entities import NormalizedChunk
from raqe.models.ingestion import ChunkItem

SECTION_LABEL_PATTERN = re.compile(r"(?P<label>\d+(?:\.\d+)*)")


def normalize_timestamp(raw_value: str | None, fallback: str) -> str:
    if not raw_value:
        return fallback
    try:
        return datetime.fromisoformat(raw_value).date().isoformat()
    except ValueError:
        return fallback


def parse_section_identity(section_title: str | None) -> tuple[str | None, str | None]:
    if not section_title:
        return None, None
    match = SECTION_LABEL_PATTERN.search(section_title)
    if not match:
        return None, None
    label = match.group("label")
    return label, f"sec_{label}"


def map_chunkitem_to_raqe(
    chunk: ChunkItem, collection_id: str, document_timestamp: str
) -> NormalizedChunk:
    section_label, section_id = parse_section_identity(chunk.section_title)
    normalized_timestamp = normalize_timestamp(chunk.publish_date, document_timestamp)
    return NormalizedChunk(
        chunk_id=chunk.chunk_id,
        collection_id=collection_id,
        document_id=chunk.doc_id,
        content=chunk.content,
        chunk_type=chunk.type,
        page=chunk.page,
        bundle_id=chunk.bundle_id,
        section_title=chunk.section_title,
        section_label=section_label,
        section_id=section_id,
        title_summary=chunk.title_summary,
        timestamp=normalized_timestamp,
        publish_date=chunk.publish_date,
        prev_chunk=chunk.prev_chunk,
        next_chunk=chunk.next_chunk,
        references=chunk.references,
    )
