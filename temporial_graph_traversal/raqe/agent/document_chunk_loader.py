from __future__ import annotations

from collections import defaultdict

from raqe.collection_namespace import to_internal
from raqe.graph.neo4j_client import get_driver
from raqe.graph.queries import LOAD_CHUNKS_FOR_DOC_IDS_QUERY


def load_document_chunks(
    collection: str,
    doc_ids: list[str],
    driver=None,
) -> dict[str, list[dict]]:
    if not collection:
        raise ValueError("collection is required")
    collection = to_internal(collection) or collection
    if not doc_ids:
        return {}

    active_driver = driver or get_driver()
    rows_by_doc: dict[str, list[dict]] = defaultdict(list)

    with active_driver.session() as session:
        records = session.run(
            LOAD_CHUNKS_FOR_DOC_IDS_QUERY,
            collection_id=collection,
            doc_ids=doc_ids,
        )
        allowed_doc_ids = set(doc_ids)
        for record in records:
            document_id = record["document_id"]
            if document_id not in allowed_doc_ids:
                continue
            row = dict(record)
            rows_by_doc[document_id].append(row)

    return dict(rows_by_doc)
