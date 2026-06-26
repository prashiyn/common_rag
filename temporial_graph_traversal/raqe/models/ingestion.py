from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ChunkReferenceItem(BaseModel):
    reference_text: str
    reference_type: str
    target_label: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChunkItem(BaseModel):
    chunk_id: str
    content: str
    type: str
    doc_id: str
    page: int | None
    bundle_id: str
    section_title: str | None
    title_summary: str
    publish_date: str | None
    prev_chunk: str | None
    next_chunk: str | None
    references: list[ChunkReferenceItem] = Field(default_factory=list)


class DocumentIngestionPayload(BaseModel):
    collection_id: str
    doc_id: str
    fiscal_year: str
    period: str
    timestamp: str
    chunks: list[ChunkItem]

    @model_validator(mode="after")
    def validate_chunk_ownership(self) -> "DocumentIngestionPayload":
        if not self.chunks:
            raise ValueError("chunks must be a non-empty list")
        mismatched = [chunk.chunk_id for chunk in self.chunks if chunk.doc_id != self.doc_id]
        if mismatched:
            raise ValueError(
                f"all chunks must match parent doc_id '{self.doc_id}', mismatched chunk_ids={mismatched}"
            )
        return self
