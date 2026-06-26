from pydantic import BaseModel


class EventItem(BaseModel):
    collection_id: str
    document_id: str
    chunk_id: str
    timestamp: str
    event_type: str


class ReferencePathItem(BaseModel):
    collection_id: str
    document_id: str
    source_chunk_id: str
    target_chunk_id: str
    hop_count: int


class TableItem(BaseModel):
    collection_id: str
    document_id: str
    source_chunk_id: str
    target_chunk_id: str | None
    target_label: str
