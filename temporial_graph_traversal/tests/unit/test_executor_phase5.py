from raqe.agent.executor import fetch_events, fetch_tables, traverse_references


def test_fetch_events_is_deduplicated_and_deterministic() -> None:
    chunks = [
        {
            "collection_id": "RELIANCE",
            "document_id": "d1",
            "chunk_id": "c1",
            "timestamp": "2024-04-30",
            "content": "Revenue increased significantly",
            "references": [],
        },
        {
            "collection_id": "RELIANCE",
            "document_id": "d1",
            "chunk_id": "c1",
            "timestamp": "2024-04-30",
            "content": "Revenue increased significantly",
            "references": [],
        },
        {
            "collection_id": "RELIANCE",
            "document_id": "d1",
            "chunk_id": "c2",
            "timestamp": "2024-03-31",
            "content": "See Table 4",
            "references": [{"reference_text": "Table 4"}],
        },
    ]
    events = fetch_events(chunks)
    assert [e["chunk_id"] for e in events] == ["c1", "c2"]
    assert events[0]["event_type"] == "TREND_CHANGE"
    assert events[1]["event_type"] == "REFERENCE_MENTION"


def test_fetch_tables_returns_table_entries_with_dedup() -> None:
    refs = [
        {
            "collection_id": "RELIANCE",
            "source_document_id": "d1",
            "source_chunk_id": "c1",
            "target_chunk_id": "t1",
            "target_label": "3",
            "reference_type": "TABLE",
        },
        {
            "collection_id": "RELIANCE",
            "source_document_id": "d1",
            "source_chunk_id": "c1",
            "target_chunk_id": "t1",
            "target_label": "3",
            "reference_type": "TABLE",
        },
    ]
    tables = fetch_tables(refs)
    assert len(tables) == 1
    assert tables[0]["target_label"] == "3"


def test_traverse_references_combines_resolved_and_graph_paths(monkeypatch) -> None:
    chunks = [
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "d1",
            "chunk_id": "c1",
            "section_label": "4.2",
            "timestamp": "2024-04-30",
            "references": [{"reference_text": "Table 3", "reference_type": "TABLE", "target_label": "3", "confidence": 0.9}],
            "content": "see table 3",
        },
        {
            "collection_id": "tgt_graph_RELIANCE",
            "document_id": "d1",
            "chunk_id": "t1",
            "section_label": "3",
            "timestamp": "2024-04-30",
            "references": [],
            "content": "table body",
        },
    ]

    monkeypatch.setattr(
        "raqe.agent.executor.traverse_reference_graph",
        lambda collection, doc_ids, chunk_ids: [  # noqa: ARG005
            {"document_id": "d1", "source_chunk_id": "c1", "target_chunk_id": "t1", "hop_count": 1}
        ],
    )
    refs = traverse_references(chunks)
    assert len(refs) >= 1
    assert any(item.get("source_chunk_id") == "c1" for item in refs)
