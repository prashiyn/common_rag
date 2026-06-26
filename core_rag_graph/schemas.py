from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExtracGraphDataResponse(BaseModel):
    """Fields for res_data-style API responses."""
    success: bool
    message: str
    graph_chunks: List[Dict] = []
    graph_vocabulary_set: set = set()
    community_reports: List[Dict] = []


# Request/Response models
class CommunityReportsResponse(BaseModel):
    """Fields for res_data-style API responses."""
    success: bool
    message: str
    community_reports: List[Dict] = []

# Request/Response models
class RequestResponse(BaseModel):
    """Fields for res_data-style API responses."""
    success: bool
    message: str


class ChunkInput(BaseModel):
    chunk_id: str = Field(..., description="Stable chunk identifier")
    content: str = Field(..., description="Chunk text, table, or image description")
    type: str = Field(..., description="One of text, table, image")
    doc_id: str = Field(..., description="Document id")
    page: Optional[int] = Field(None, description="Source page when available")
    bundle_id: str = Field(..., description="Semantic bundle id")
    section_title: Optional[str] = Field(None, description="Nearest section heading")
    title_summary: str = Field("", description="LLM section summary")
    publish_date: Optional[str] = Field(None, description="Document publish date if provided")
    prev_chunk: Optional[str] = Field(None, description="Previous chunk id")
    next_chunk: Optional[str] = Field(None, description="Next chunk id")


class CollectionScopedRequest(BaseModel):
    collection_id: str
    client_id: str = "default"


class IngestChunksRequest(CollectionScopedRequest):
    chunks: List[ChunkInput]
    file_name: str
    temperature: float = 0.001
    schema: Optional[Dict[str, Any]] = None


class CommunityReportsRequest(CollectionScopedRequest):
    pass


class DeleteFileRequest(CollectionScopedRequest):
    file_name: str


class GetGraphRequest(CollectionScopedRequest):
    kb_id: Optional[str] = None


class RetrieveRequest(CollectionScopedRequest):
    query: str
    top_k: int = 10


class QueryRequest(CollectionScopedRequest):
    question: str
    top_k: int = 10
    temperature: float = 0.001


class TestPostRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class CollectionMetadata(BaseModel):
    collection_id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str


class CollectionResponse(BaseModel):
    success: bool
    message: str
    collection: CollectionMetadata


class CollectionListResponse(BaseModel):
    success: bool
    message: str
    collections: List[CollectionMetadata]


class GetOrCreateCollectionRequest(BaseModel):
    collection_id: str
    name: Optional[str] = None
    description: str = ""


class GetCollectionByIdRequest(BaseModel):
    collection_id: str


class GraphDataResponse(BaseModel):
    """Fields for res_data-style API responses."""
    success: bool
    message: str
    graph_data: dict


class RetrieveResponse(BaseModel):
    success: bool
    message: str
    query: str
    collection_id: str
    evidence: List[Dict]
    chunk_evidence: List[Dict] = []


class QueryResponse(BaseModel):
    success: bool
    message: str
    question: str
    collection_id: str
    answer: str
    evidence: List[Dict]
    chunk_evidence: List[Dict] = []

