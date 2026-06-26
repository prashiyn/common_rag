from raqe.agent.context_builder import build_context


def test_context_builder_includes_summary_and_provenance() -> None:
    data = {
        "documents": [{"document_id": "d1"}, {"document_id": "d2"}],
        "filtered_chunks": [
            {
                "collection_id": "tgt_graph_RELIANCE",
                "document_id": "d1",
                "chunk_id": "c1",
                "timestamp": "2024-04-30",
                "section_title": "4.2 Revenue",
                "section_label": "4.2",
                "title_summary": "Revenue",
                "content": "Revenue increased strongly",
            }
        ],
        "events": [{"dummy": True}],
        "references": [
            {
                "source_chunk_id": "c1",
                "reference_text": "Table 3",
                "reference_type": "TABLE",
                "target_label": "3",
                "resolved": False,
                "reason": "no candidates",
            }
        ],
        "tables": [
            {
                "collection_id": "tgt_graph_RELIANCE",
                "document_id": "d1",
                "source_chunk_id": "c1",
                "target_chunk_id": "t1",
                "target_label": "3",
            }
        ],
    }
    context = build_context(data)
    assert context["summary"]["document_count"] == 2
    assert context["summary"]["chunk_count"] == 1
    assert context["summary"]["reference_count"] == 1
    assert context["evidence"][0]["collection_id"] == "tgt_graph_RELIANCE"
    assert context["reference_traces"][0]["resolved"] is False

