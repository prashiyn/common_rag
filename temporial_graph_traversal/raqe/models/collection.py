from pydantic import BaseModel


class CollectionSummary(BaseModel):
    id: str
    name: str


class CollectionMetadata(BaseModel):
    id: str
    name: str
    document_count: int
    chunk_count: int
    earliest_timestamp: str | None = None
    latest_timestamp: str | None = None


class GetOrCreateCollectionRequest(BaseModel):
    collection_id: str
    name: str | None = None
