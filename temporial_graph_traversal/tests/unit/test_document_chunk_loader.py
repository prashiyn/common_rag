import pytest

from raqe.agent.document_chunk_loader import load_document_chunks
from raqe.graph import queries


class FakeSession:
    def __init__(self, records):
        self.records = records
        self.last_query = None
        self.last_params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.last_query = query
        self.last_params = params
        return self.records


class FakeDriver:
    def __init__(self, records):
        self.session_obj = FakeSession(records)

    def session(self):
        return self.session_obj


def test_loader_requires_collection() -> None:
    with pytest.raises(ValueError, match="collection is required"):
        load_document_chunks("", ["doc_1"], driver=FakeDriver([]))


def test_loader_returns_empty_dict_for_empty_doc_ids() -> None:
    assert load_document_chunks("RELIANCE", [], driver=FakeDriver([])) == {}


def test_loader_groups_by_document_and_enforces_doc_scope() -> None:
    records = [
        {"document_id": "doc_1", "chunk_id": "c1", "timestamp": "2024-04-30"},
        {"document_id": "doc_1", "chunk_id": "c2", "timestamp": "2024-04-30"},
        {"document_id": "doc_2", "chunk_id": "c3", "timestamp": "2024-03-31"},
        {"document_id": "doc_3", "chunk_id": "c4", "timestamp": "2024-03-31"},
    ]
    driver = FakeDriver(records)
    result = load_document_chunks("RELIANCE", ["doc_1", "doc_2"], driver=driver)

    assert driver.session_obj.last_query == queries.LOAD_CHUNKS_FOR_DOC_IDS_QUERY
    assert driver.session_obj.last_params == {"collection_id": "tgt_graph_RELIANCE", "doc_ids": ["doc_1", "doc_2"]}
    assert set(result.keys()) == {"doc_1", "doc_2"}
    assert [row["chunk_id"] for row in result["doc_1"]] == ["c1", "c2"]
