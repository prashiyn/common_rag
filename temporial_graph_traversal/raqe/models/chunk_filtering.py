from pydantic import BaseModel, Field


class FilteredChunk(BaseModel):
    collection_id: str
    document_id: str
    chunk_id: str
    content: str
    title_summary: str
    section_title: str | None
    section_label: str | None
    timestamp: str
    references: list[dict] = Field(default_factory=list)
    score: float
    match_reasons: list[str] = Field(default_factory=list)
