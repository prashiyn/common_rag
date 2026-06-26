from pydantic import BaseModel, Field


class ReferenceCandidate(BaseModel):
    collection_id: str
    document_id: str
    chunk_id: str
    section_label: str | None
    timestamp: str
    confidence: float = 0.0


class ResolvedReference(BaseModel):
    source_chunk_id: str
    source_document_id: str
    collection_id: str
    reference_text: str
    reference_type: str
    target_label: str
    resolved: bool
    target_chunk_id: str | None = None
    target_document_id: str | None = None
    target_section_label: str | None = None
    score: float | None = None
    reason: str
    ranked_candidates: list[dict] = Field(default_factory=list)
