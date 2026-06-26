from raqe.structure.disambiguator import disambiguate


def test_disambiguator_prefers_same_document_first() -> None:
    candidates = [
        {"document_id": "doc_2", "section_label": "4.2", "timestamp": "2024-04-30", "confidence": 0.9, "chunk_id": "b"},
        {"document_id": "doc_1", "section_label": "9.1", "timestamp": "2024-04-30", "confidence": 0.9, "chunk_id": "a"},
    ]
    ranked = disambiguate(candidates, {"source_document_id": "doc_1", "source_section_label": "4.2"})
    assert ranked[0]["document_id"] == "doc_1"


def test_disambiguator_uses_section_proximity_then_timestamp_then_confidence() -> None:
    candidates = [
        {"document_id": "doc_1", "section_label": "4.3", "timestamp": "2024-03-31", "confidence": 0.7, "chunk_id": "c"},
        {"document_id": "doc_1", "section_label": "4.21", "timestamp": "2024-04-30", "confidence": 0.8, "chunk_id": "a"},
        {"document_id": "doc_1", "section_label": "4.21", "timestamp": "2024-04-29", "confidence": 0.99, "chunk_id": "b"},
    ]
    ranked = disambiguate(candidates, {"source_document_id": "doc_1", "source_section_label": "4.2"})
    assert ranked[0]["chunk_id"] == "c"


def test_disambiguator_handles_hierarchical_sections() -> None:
    candidates = [
        {"document_id": "doc_1", "section_label": "4.2.8", "timestamp": "2024-04-30", "confidence": 0.8, "chunk_id": "far"},
        {"document_id": "doc_1", "section_label": "4.2.1", "timestamp": "2024-04-30", "confidence": 0.8, "chunk_id": "near"},
    ]
    ranked = disambiguate(candidates, {"source_document_id": "doc_1", "source_section_label": "4.2.0"})
    assert ranked[0]["chunk_id"] == "near"
