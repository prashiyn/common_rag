from raqe.agent.answer_generator import generate_answer


def test_answer_generator_returns_structured_contract() -> None:
    context = {
        "summary": {
            "document_count": 1,
            "chunk_count": 2,
            "event_count": 2,
            "reference_count": 2,
            "table_count": 1,
        },
        "evidence": [
            {"document_id": "d1", "chunk_id": "c1", "title_summary": "Revenue"},
        ],
        "reference_traces": [
            {"reference_text": "Table 3", "resolved": True},
            {"reference_text": "Table 9", "resolved": False},
        ],
    }
    answer = generate_answer("Why revenue increased?", context)
    assert answer["question"] == "Why revenue increased?"
    assert 0.0 <= answer["confidence"] <= 1.0
    assert "documents=1" in answer["context_summary"]
    assert len(answer["supporting_facts"]) >= 1

