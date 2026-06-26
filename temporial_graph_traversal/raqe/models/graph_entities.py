from __future__ import annotations

from pydantic import BaseModel, Field

from raqe.models.ingestion import ChunkReferenceItem


class NormalizedChunk(BaseModel):
    chunk_id: str
    collection_id: str
    document_id: str
    content: str
    chunk_type: str
    page: int | None
    bundle_id: str
    section_title: str | None
    section_label: str | None
    section_id: str | None
    title_summary: str
    timestamp: str
    publish_date: str | None
    prev_chunk: str | None
    next_chunk: str | None
    references: list[ChunkReferenceItem] = Field(default_factory=list)
