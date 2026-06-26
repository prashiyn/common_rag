from raqe.agent.query_engine import run_query


def test_run_query_returns_phase6_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        "raqe.agent.query_engine.parse_query",
        lambda question, collection_override=None, section_hint=None: {  # noqa: ARG005
            "intent": "WHY",
            "collection": "tgt_graph_RELIANCE",
            "time_context": {"raw_text": "latest", "mode": "latest_fallback", "needs_fallback": True},
            "target": question,
        },
    )
    monkeypatch.setattr(
        "raqe.agent.query_engine.build_plan",
        lambda parsed: {"steps": ["resolve_documents"], "parsed_query": parsed},
    )
    monkeypatch.setattr(
        "raqe.agent.query_engine.execute_plan",
        lambda plan, query: {
            "documents": [{"document_id": "d1"}],
            "filtered_chunks": [
                {
                    "collection_id": "tgt_graph_RELIANCE",
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "timestamp": "2024-04-30",
                    "section_title": "4.2 Revenue",
                    "section_label": "4.2",
                    "title_summary": "Revenue",
                    "content": "Revenue up",
                    "references": [],
                }
            ],
            "events": [],
            "references": [],
            "tables": [],
        },
    )

    result = run_query("Why revenue increased?")
    assert "parsed_query" in result
    assert "plan" in result
    assert "execution" in result
    assert "context" in result
    assert "answer" in result
    assert result["context"]["summary"]["chunk_count"] == 1
    assert "direct_answer" in result["answer"]

