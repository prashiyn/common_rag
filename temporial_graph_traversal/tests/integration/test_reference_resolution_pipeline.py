from raqe.agent.executor import traverse_references


def test_traverse_references_resolves_and_keeps_scope() -> None:
    chunks = [
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "doc_1",
            "chunk_id": "src",
            "section_label": "4.2",
            "timestamp": "2024-04-30",
            "content": "see table 3",
            "references": [
                {"reference_text": "Table 3", "reference_type": "TABLE", "target_label": "3", "confidence": 0.9}
            ],
        },
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "doc_1",
            "chunk_id": "target_same_doc",
            "section_label": "3",
            "timestamp": "2024-04-30",
            "content": "table data",
            "references": [],
        },
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "doc_2",
            "chunk_id": "target_other_doc",
            "section_label": "3",
            "timestamp": "2024-04-30",
            "content": "table data",
            "references": [],
        },
        {
            "collection_id": "tgt_graph_INFY",
            "document_id": "doc_x",
            "chunk_id": "cross_collection",
            "section_label": "3",
            "timestamp": "2024-04-30",
            "content": "table data",
            "references": [],
        },
    ]
    resolved = traverse_references(chunks)
    assert len(resolved) == 1
    assert resolved[0]["resolved"] is True
    assert resolved[0]["target_chunk_id"] == "target_same_doc"
    assert resolved[0]["target_document_id"] in {"doc_1", "doc_2"}
    assert all(c["collection_id"] == "tgt_graph_RELIANCE" for c in resolved[0]["ranked_candidates"])


def test_traverse_references_returns_unresolved_when_no_candidates() -> None:
    chunks = [
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "doc_1",
            "chunk_id": "src",
            "section_label": "4.2",
            "timestamp": "2024-04-30",
            "content": "see table 9",
            "references": [
                {"reference_text": "Table 9", "reference_type": "TABLE", "target_label": "9", "confidence": 0.9}
            ],
        }
    ]
    resolved = traverse_references(chunks)
    assert len(resolved) == 1
    assert resolved[0]["resolved"] is False
