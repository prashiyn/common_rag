from __future__ import annotations

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from raqe.collection_namespace import to_internal
from raqe.graph.neo4j_client import get_driver
from raqe.graph.queries import TRAVERSE_REFERENCE_MULTI_HOP_QUERY


def traverse_reference_graph(
    collection: str,
    doc_ids: list[str],
    chunk_ids: list[str],
    max_hops: int = 2,
    driver=None,
) -> list[dict]:
    if not collection:
        raise ValueError("collection is required")
    collection = to_internal(collection) or collection
    if not doc_ids or not chunk_ids:
        return []
    if max_hops < 1:
        return []

    active_driver = driver or get_driver()
    try:
        with active_driver.session() as session:
            rows = session.run(
                TRAVERSE_REFERENCE_MULTI_HOP_QUERY,
                collection_id=collection,
                doc_ids=doc_ids,
                chunk_ids=chunk_ids,
            )
            deduped: dict[tuple[str, str, str, int], dict] = {}
            for row in rows:
                payload = dict(row)
                key = (
                    payload.get("document_id", ""),
                    payload.get("source_chunk_id", ""),
                    payload.get("target_chunk_id", ""),
                    int(payload.get("hop_count", 0)),
                )
                if key[1] == "":
                    continue
                deduped[key] = payload
            return [deduped[k] for k in sorted(deduped.keys())]
    except (ServiceUnavailable, Neo4jError):
        return []
