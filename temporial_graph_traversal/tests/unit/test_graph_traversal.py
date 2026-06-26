import pytest
from neo4j.exceptions import ServiceUnavailable

from raqe.graph import queries
from raqe.graph.traversal import traverse_reference_graph


class FakeSession:
    def __init__(self, rows=None, should_fail=False):
        self.rows = rows or []
        self.should_fail = should_fail
        self.last_query = None
        self.last_params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.last_query = query
        self.last_params = params
        if self.should_fail:
            raise ServiceUnavailable("unavailable")
        return self.rows


class FakeDriver:
    def __init__(self, rows=None, should_fail=False):
        self.session_obj = FakeSession(rows=rows, should_fail=should_fail)

    def session(self):
        return self.session_obj


def test_traversal_short_circuits_empty_inputs() -> None:
    assert traverse_reference_graph("RELIANCE", [], ["c1"], driver=FakeDriver()) == []
    assert traverse_reference_graph("RELIANCE", ["d1"], [], driver=FakeDriver()) == []


def test_traversal_executes_scoped_query_and_deduplicates() -> None:
    rows = [
        {"document_id": "d1", "source_chunk_id": "c1", "target_chunk_id": "t1", "hop_count": 1},
        {"document_id": "d1", "source_chunk_id": "c1", "target_chunk_id": "t1", "hop_count": 1},
        {"document_id": "d1", "source_chunk_id": "c1", "target_chunk_id": "t2", "hop_count": 2},
    ]
    driver = FakeDriver(rows=rows)
    result = traverse_reference_graph("RELIANCE", ["d1"], ["c1"], driver=driver)
    assert driver.session_obj.last_query == queries.TRAVERSE_REFERENCE_MULTI_HOP_QUERY
    assert driver.session_obj.last_params["collection_id"] == "tgt_graph_RELIANCE"
    assert len(result) == 2


def test_traversal_returns_empty_on_backend_failure() -> None:
    result = traverse_reference_graph("RELIANCE", ["d1"], ["c1"], driver=FakeDriver(should_fail=True))
    assert result == []


def test_traversal_requires_collection() -> None:
    with pytest.raises(ValueError, match="collection is required"):
        traverse_reference_graph("", ["d1"], ["c1"], driver=FakeDriver())
