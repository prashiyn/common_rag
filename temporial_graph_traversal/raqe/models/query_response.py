from pydantic import BaseModel, Field


class ContextSummary(BaseModel):
    document_count: int
    chunk_count: int
    event_count: int
    reference_count: int
    table_count: int


class ContextEvidenceItem(BaseModel):
    collection_id: str
    document_id: str
    chunk_id: str
    timestamp: str
    section_title: str | None
    section_label: str | None
    title_summary: str
    content_snippet: str


class ReferenceTraceItem(BaseModel):
    source_chunk_id: str
    reference_text: str
    reference_type: str
    target_label: str
    resolved: bool
    reason: str
    target_chunk_id: str | None = None
    target_document_id: str | None = None


class TableEvidenceItem(BaseModel):
    collection_id: str
    document_id: str
    source_chunk_id: str
    target_chunk_id: str | None
    target_label: str


class QueryContext(BaseModel):
    summary: ContextSummary
    documents: list[dict] = Field(default_factory=list)
    evidence: list[ContextEvidenceItem] = Field(default_factory=list)
    reference_traces: list[ReferenceTraceItem] = Field(default_factory=list)
    table_evidence: list[TableEvidenceItem] = Field(default_factory=list)


class QueryAnswer(BaseModel):
    question: str
    direct_answer: str
    confidence: float
    context_summary: str
    supporting_facts: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    parsed_query: dict
    plan: dict
    execution: dict
    context: QueryContext
    answer: QueryAnswer
