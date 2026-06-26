from raqe.agent.document_resolver import DocumentResolver
from raqe.agent.time_resolver import parse_time
from raqe.graph import queries


class FakeSession:
    def __init__(self, data_by_query):
        self.data_by_query = data_by_query

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        rows = self.data_by_query.get(query, [])
        if query in {
            queries.RESOLVE_DOCUMENTS_BY_QUARTER_QUERY,
            queries.RESOLVE_DOCUMENTS_BY_FISCAL_YEAR_QUERY,
            queries.RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY,
            queries.RESOLVE_LATEST_DOCUMENTS_QUERY,
        }:
            scoped = [row for row in rows if row["collection_id"] == params["collection_id"]]
            return [{"doc_id": r["doc_id"], "timestamp": r["timestamp"]} for r in scoped]
        return []


class FakeDriver:
    def __init__(self, data_by_query):
        self.data_by_query = data_by_query

    def session(self):
        return FakeSession(self.data_by_query)


def test_q1_fy24_returns_only_matching_collection_docs() -> None:
    driver = FakeDriver(
        {
                queries.RESOLVE_DOCUMENTS_BY_QUARTER_QUERY: [
                    {"collection_id": "tgt_graph_RELIANCE", "doc_id": "rel_q1_fy24", "timestamp": "2024-04-30"},
                    {"collection_id": "tgt_graph_INFY", "doc_id": "infy_q1_fy24", "timestamp": "2024-04-30"},
                ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = parse_time("Q1 FY24 for RELIANCE")
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["rel_q1_fy24"]


def test_latest_returns_newest_docs_within_collection_only() -> None:
    driver = FakeDriver(
        {
                queries.RESOLVE_LATEST_DOCUMENTS_QUERY: [
                    {"collection_id": "tgt_graph_RELIANCE", "doc_id": "rel_2024_q2", "timestamp": "2024-06-30"},
                    {"collection_id": "tgt_graph_RELIANCE", "doc_id": "rel_2024_q1", "timestamp": "2024-04-30"},
                    {"collection_id": "tgt_graph_INFY", "doc_id": "infy_2024_q2", "timestamp": "2024-06-30"},
                ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = parse_time("latest performance for RELIANCE")
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["rel_2024_q2", "rel_2024_q1"]


def test_non_matching_explicit_range_returns_empty_without_widening_scope() -> None:
    driver = FakeDriver({queries.RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY: []})
    resolver = DocumentResolver(driver=driver)
    context = parse_time("between 2020-01-01 and 2020-03-31 for RELIANCE")
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == []
    assert result.fallback_used is False
