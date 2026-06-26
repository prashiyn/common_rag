from raqe.models.query_response import (
    ContextEvidenceItem,
    ContextSummary,
    QueryContext,
    ReferenceTraceItem,
    TableEvidenceItem,
)


def _snippet(content: str, limit: int = 180) -> str:
    if len(content) <= limit:
        return content
    return content[:limit].rstrip() + "..."


def build_context(data: dict) -> dict:
    documents = sorted(data.get("documents", []), key=lambda item: item.get("document_id", ""))
    chunks = data.get("filtered_chunks", [])
    references = data.get("references", [])
    tables = data.get("tables", [])

    evidence_items = [
        ContextEvidenceItem(
            collection_id=chunk.get("collection_id", ""),
            document_id=chunk.get("document_id", ""),
            chunk_id=chunk.get("chunk_id", ""),
            timestamp=chunk.get("timestamp", ""),
            section_title=chunk.get("section_title"),
            section_label=chunk.get("section_label"),
            title_summary=chunk.get("title_summary", ""),
            content_snippet=_snippet(chunk.get("content", "")),
        )
        for chunk in chunks
    ]
    evidence_items.sort(key=lambda item: (item.timestamp, item.chunk_id), reverse=True)

    reference_traces = [
        ReferenceTraceItem(
            source_chunk_id=ref.get("source_chunk_id", ""),
            reference_text=ref.get("reference_text", ""),
            reference_type=ref.get("reference_type", "OTHER"),
            target_label=ref.get("target_label", ""),
            resolved=bool(ref.get("resolved", False)),
            reason=ref.get("reason", ""),
            target_chunk_id=ref.get("target_chunk_id"),
            target_document_id=ref.get("target_document_id"),
        )
        for ref in references
        if ref.get("reference_text") is not None or ref.get("source_chunk_id")
    ]

    table_evidence = [
        TableEvidenceItem(
            collection_id=table.get("collection_id", ""),
            document_id=table.get("document_id", ""),
            source_chunk_id=table.get("source_chunk_id", ""),
            target_chunk_id=table.get("target_chunk_id"),
            target_label=table.get("target_label", ""),
        )
        for table in tables
    ]

    context = QueryContext(
        summary=ContextSummary(
            document_count=len(documents),
            chunk_count=len(chunks),
            event_count=len(data.get("events", [])),
            reference_count=len(references),
            table_count=len(tables),
        ),
        documents=documents,
        evidence=evidence_items,
        reference_traces=reference_traces,
        table_evidence=table_evidence,
    )
    return context.model_dump()
