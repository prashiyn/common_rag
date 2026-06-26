from raqe.structure.resolver import normalize_reference_label, resolve_reference


def test_normalize_reference_label_prefers_target_label() -> None:
    assert normalize_reference_label("Table 3", "03") == "03"


def test_normalize_reference_label_extracts_from_text() -> None:
    assert normalize_reference_label("Table 3", None) == "3"


def test_resolve_reference_filters_scope_and_resolves() -> None:
    source_chunk = {"chunk_id": "src", "document_id": "doc_1", "section_label": "4.2"}
    ref = {"reference_text": "Table 3", "reference_type": "TABLE", "target_label": "3", "confidence": 0.95}
    candidates = [
        {"collection_id": "tgt_graph_RELIANCE", "document_id": "doc_1", "chunk_id": "a", "section_label": "3", "timestamp": "2024-04-30", "content": ""},
        {"collection_id": "tgt_graph_INFY", "document_id": "doc_1", "chunk_id": "b", "section_label": "3", "timestamp": "2024-04-30", "content": ""},
    ]
    resolved = resolve_reference(ref, "RELIANCE", ["doc_1"], source_chunk, candidates)
    assert resolved["resolved"] is True
    assert resolved["target_chunk_id"] == "a"


def test_resolve_reference_unresolved_with_reason() -> None:
    source_chunk = {"chunk_id": "src", "document_id": "doc_1", "section_label": "4.2"}
    ref = {"reference_text": "Table 9", "reference_type": "TABLE", "target_label": "9", "confidence": 0.2}
    resolved = resolve_reference(ref, "RELIANCE", ["doc_1"], source_chunk, [])
    assert resolved["resolved"] is False
    assert "no candidates" in resolved["reason"]
