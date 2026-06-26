from raqe.agent.chunk_filter import filter_chunks
from raqe.agent.document_resolver import resolve_documents
from raqe.collection_namespace import to_internal
from raqe.graph.traversal import traverse_reference_graph
from raqe.models.execution import EventItem, ReferencePathItem, TableItem
from raqe.models.time_context import TimeContext
from raqe.structure.resolver import resolve_structure_references


def filter_documents(collection: str, time_context: dict) -> list[dict]:
    context = TimeContext(**time_context)
    doc_ids = resolve_documents(collection, context)
    return [{"document_id": doc_id} for doc_id in doc_ids]


def get_filtered_chunks(collection: str, query: dict, docs: list[dict]) -> list[dict]:
    doc_ids = [doc["document_id"] for doc in docs]
    section_hint = query.get("section_hint")
    return filter_chunks(
        collection=collection,
        doc_ids=doc_ids,
        target=query.get("target"),
        section_hint=section_hint,
    )


def fetch_events(chunks: list[dict]) -> list[dict]:
    dedup: dict[tuple[str, str], dict] = {}
    for chunk in chunks:
        content = str(chunk.get("content", "")).lower()
        references = chunk.get("references", [])
        if references:
            event_type = "REFERENCE_MENTION"
        elif any(keyword in content for keyword in ("increase", "decrease", "grew", "decline", "drop", "rise")):
            event_type = "TREND_CHANGE"
        elif any(keyword in content for keyword in ("risk", "penalty", "regulation", "compliance")):
            event_type = "RISK_SIGNAL"
        else:
            event_type = "CONTENT_MENTION"
        key = (chunk["document_id"], chunk["chunk_id"])
        dedup[key] = EventItem(
            collection_id=chunk["collection_id"],
            document_id=chunk["document_id"],
            chunk_id=chunk["chunk_id"],
            timestamp=chunk.get("timestamp", ""),
            event_type=event_type,
        ).model_dump()
    return [dedup[k] for k in sorted(dedup.keys())]


def traverse_references(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    collection = to_internal(chunks[0]["collection_id"]) or chunks[0]["collection_id"]
    doc_ids = sorted({chunk["document_id"] for chunk in chunks})
    resolved_references = resolve_structure_references(
        collection=collection,
        doc_ids=doc_ids,
        filtered_chunks=chunks,
    )
    chunk_ids = sorted({chunk["chunk_id"] for chunk in chunks})
    graph_paths = traverse_reference_graph(collection=collection, doc_ids=doc_ids, chunk_ids=chunk_ids)
    path_items = [
        ReferencePathItem(
            collection_id=collection,
            document_id=row["document_id"],
            source_chunk_id=row["source_chunk_id"],
            target_chunk_id=row.get("target_chunk_id", ""),
            hop_count=int(row.get("hop_count", 0)),
        ).model_dump()
        for row in graph_paths
        if row.get("source_chunk_id")
    ]
    dedup: dict[tuple[str, str, str], dict] = {}
    for ref in resolved_references:
        key = (
            ref.get("source_chunk_id", ""),
            ref.get("target_chunk_id") or "",
            ref.get("target_label", ""),
        )
        dedup[key] = ref
    for path in path_items:
        key = (path["source_chunk_id"], path["target_chunk_id"], "")
        dedup[key] = path
    return list(dedup.values())


def fetch_tables(references: list[dict]) -> list[dict]:
    dedup: dict[tuple[str, str, str], dict] = {}
    for ref in references:
        is_table = str(ref.get("reference_type", "")).upper() == "TABLE"
        if not is_table and not ref.get("target_label"):
            continue
        source_chunk_id = ref.get("source_chunk_id")
        if not source_chunk_id:
            continue
        target_label = ref.get("target_label") or ""
        target_chunk_id = ref.get("target_chunk_id")
        key = (source_chunk_id, target_chunk_id or "", target_label)
        dedup[key] = TableItem(
            collection_id=ref.get("collection_id", ""),
            document_id=ref.get("source_document_id") or ref.get("document_id", ""),
            source_chunk_id=source_chunk_id,
            target_chunk_id=target_chunk_id,
            target_label=target_label,
        ).model_dump()
    return [dedup[k] for k in sorted(dedup.keys())]


def execute_plan(plan: dict, query: dict) -> dict:
    query = {**query}
    if query.get("collection"):
        query["collection"] = to_internal(query["collection"]) or query["collection"]
    docs = filter_documents(query["collection"], query["time_context"])
    filtered_chunks = get_filtered_chunks(query["collection"], query, docs)
    events = fetch_events(filtered_chunks)
    refs = traverse_references(filtered_chunks)
    tables = fetch_tables(refs)
    return {
        "documents": docs,
        "filtered_chunks": filtered_chunks,
        "events": events,
        "references": refs,
        "tables": tables,
    }
