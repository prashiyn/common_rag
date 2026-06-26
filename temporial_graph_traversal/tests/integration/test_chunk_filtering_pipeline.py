from raqe.agent.executor import execute_plan


def test_executor_includes_filtered_chunks_and_respects_scoped_docs(monkeypatch) -> None:
    def fake_resolve_documents(collection, time_context, driver=None):  # noqa: ARG001
        assert collection == "tgt_graph_RELIANCE"
        return ["doc_1", "doc_2"]

    def fake_load_document_chunks(collection, doc_ids, driver=None):  # noqa: ARG001
        assert collection == "tgt_graph_RELIANCE"
        assert doc_ids == ["doc_1", "doc_2"]
        return {
            "doc_1": [
                {
                    "chunk_id": "c1",
                    "content": "Revenue up",
                    "title_summary": "Revenue",
                    "section_title": "4.2 Revenue",
                    "section_label": "4.2",
                    "timestamp": "2024-04-30",
                    "references": [],
                }
            ],
            "doc_2": [
                {
                    "chunk_id": "c2",
                    "content": "Costs up",
                    "title_summary": "Costs",
                    "section_title": "5 Costs",
                    "section_label": "5",
                    "timestamp": "2024-03-31",
                    "references": [],
                }
            ],
            "doc_3": [
                {
                    "chunk_id": "leak",
                    "content": "Should not appear",
                    "title_summary": "Leak",
                    "section_title": "9 Leak",
                    "section_label": "9",
                    "timestamp": "2024-03-31",
                    "references": [],
                }
            ],
        }

    monkeypatch.setattr("raqe.agent.executor.resolve_documents", fake_resolve_documents)
    monkeypatch.setattr("raqe.agent.chunk_filter.load_document_chunks", fake_load_document_chunks)

    query = {
        "collection": "RELIANCE",
        "time_context": {"raw_text": "latest", "mode": "latest_fallback", "needs_fallback": True},
        "target": "revenue",
    }
    result = execute_plan(plan={"steps": []}, query=query)
    assert [doc["document_id"] for doc in result["documents"]] == ["doc_1", "doc_2"]
    assert [chunk["chunk_id"] for chunk in result["filtered_chunks"]] == ["c1", "c2"]
    assert all(chunk["document_id"] in {"doc_1", "doc_2"} for chunk in result["filtered_chunks"])


def test_executor_returns_empty_chunks_for_empty_resolved_docs(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.agent.executor.resolve_documents",
        lambda collection, time_context, driver=None: [],  # noqa: ARG005
    )
    result = execute_plan(
        plan={"steps": []},
        query={
            "collection": "RELIANCE",
            "time_context": {"raw_text": "latest", "mode": "latest_fallback", "needs_fallback": True},
            "target": "margin",
        },
    )
    assert result["documents"] == []
    assert result["filtered_chunks"] == []
