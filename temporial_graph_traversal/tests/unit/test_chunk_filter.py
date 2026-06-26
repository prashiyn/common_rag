import pytest

from raqe.agent.chunk_filter import filter_chunks


def _fake_loader(collection, doc_ids, driver=None):  # noqa: ARG001
    assert collection == "tgt_graph_RELIANCE"
    return {
        "doc_1": [
            {
                "chunk_id": "a",
                "content": "Revenue grew strongly with margin expansion",
                "title_summary": "Quarterly revenue analysis",
                "section_title": "4.2 Revenue",
                "section_label": "4.2",
                "timestamp": "2024-04-30",
                "references": [{"reference_text": "Table 3"}],
            },
            {
                "chunk_id": "b",
                "content": "Debt levels decreased",
                "title_summary": "Balance sheet summary",
                "section_title": "5.1 Leverage",
                "section_label": "5.1",
                "timestamp": "2024-04-29",
                "references": [],
            },
        ],
        "doc_2": [
            {
                "chunk_id": "c",
                "content": "Revenue remained flat",
                "title_summary": "Revenue outlook",
                "section_title": "4 Revenue",
                "section_label": "4",
                "timestamp": "2024-03-31",
                "references": [],
            }
        ],
    }


def test_filter_requires_collection() -> None:
    with pytest.raises(ValueError, match="collection is required"):
        filter_chunks("", ["doc_1"])


def test_filter_returns_empty_for_empty_doc_ids() -> None:
    assert filter_chunks("RELIANCE", []) == []


def test_filter_scoring_and_match_reasons(monkeypatch) -> None:
    monkeypatch.setattr("raqe.agent.chunk_filter.load_document_chunks", _fake_loader)
    result = filter_chunks("RELIANCE", ["doc_1", "doc_2"], target="revenue", section_hint="4.2")
    assert [row["chunk_id"] for row in result] == ["a", "c", "b"]
    assert result[0]["score"] == 7.5
    assert "target_in_content" in result[0]["match_reasons"]
    assert "target_in_title_summary" in result[0]["match_reasons"]
    assert "section_hint_match" in result[0]["match_reasons"]
    assert "has_references" in result[0]["match_reasons"]


def test_filter_no_target_returns_recency_order(monkeypatch) -> None:
    monkeypatch.setattr("raqe.agent.chunk_filter.load_document_chunks", _fake_loader)
    result = filter_chunks("RELIANCE", ["doc_1", "doc_2"])
    assert [row["chunk_id"] for row in result] == ["a", "b", "c"]
