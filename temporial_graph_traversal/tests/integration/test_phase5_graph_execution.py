from raqe.agent.executor import execute_plan


def test_execute_plan_phase5_returns_deduped_intermediate_outputs(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.agent.executor.resolve_documents",
        lambda collection, time_context, driver=None: ["d1"],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "raqe.agent.executor.filter_chunks",
        lambda collection, doc_ids, target=None, section_hint=None: [  # noqa: ARG005
            {
                "collection_id": "tgt_graph_RELIANCE",
                "document_id": "d1",
                "chunk_id": "c1",
                "content": "see table 3",
                "title_summary": "summary",
                "section_title": "4.2 Revenue",
                "section_label": "4.2",
                "timestamp": "2024-04-30",
                "references": [{"reference_text": "Table 3", "reference_type": "TABLE", "target_label": "3", "confidence": 0.9}],
                "score": 5.0,
                "match_reasons": ["target_in_content"],
            },
            {
                "collection_id": "tgt_graph_RELIANCE",
                "document_id": "d1",
                "chunk_id": "t1",
                "content": "table body",
                "title_summary": "table",
                "section_title": "3",
                "section_label": "3",
                "timestamp": "2024-04-30",
                "references": [],
                "score": 1.0,
                "match_reasons": [],
            },
        ],
    )
    monkeypatch.setattr(
        "raqe.agent.executor.traverse_reference_graph",
        lambda collection, doc_ids, chunk_ids: [  # noqa: ARG005
            {"document_id": "d1", "source_chunk_id": "c1", "target_chunk_id": "t1", "hop_count": 1}
        ],
    )
    result = execute_plan(
        plan={"steps": []},
        query={
            "collection": "RELIANCE",
            "time_context": {"raw_text": "latest", "mode": "latest_fallback", "needs_fallback": True},
            "target": "revenue",
        },
    )
    assert result["documents"] == [{"document_id": "d1"}]
    assert len(result["events"]) == 2
    assert len(result["references"]) >= 1
    assert len(result["tables"]) >= 1
    assert all(r.get("collection_id", "tgt_graph_RELIANCE") == "tgt_graph_RELIANCE" for r in result["references"])
