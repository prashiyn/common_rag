import pytest

from raqe.agent.document_resolver import DocumentResolver
from raqe.graph import queries
from raqe.models.time_context import TimeContext


class FakeSession:
    def __init__(self, response_by_query: dict[str, list[dict]]):
        self.response_by_query = response_by_query

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query: str, **params):
        return self.response_by_query.get(query, [])


class FakeDriver:
    def __init__(self, response_by_query: dict[str, list[dict]]):
        self.response_by_query = response_by_query

    def session(self):
        return FakeSession(self.response_by_query)


def test_resolve_by_quarter_returns_deterministic_order() -> None:
    driver = FakeDriver(
        {
            queries.RESOLVE_DOCUMENTS_BY_QUARTER_QUERY: [
                {"doc_id": "doc_b", "timestamp": "2024-04-30"},
                {"doc_id": "doc_a", "timestamp": "2024-04-30"},
            ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = TimeContext(raw_text="Q1 FY24", mode="quarter", period="Q1", fiscal_year="FY2024")
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["doc_b", "doc_a"]
    assert result.fallback_used is False


def test_resolve_by_date_range() -> None:
    driver = FakeDriver(
        {
            queries.RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY: [
                {"doc_id": "doc_2", "timestamp": "2024-06-30"},
                {"doc_id": "doc_1", "timestamp": "2024-03-31"},
            ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = TimeContext(
        raw_text="between 2024-01-01 and 2024-06-30",
        mode="explicit_range",
        start_date="2024-01-01",
        end_date="2024-06-30",
    )
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["doc_2", "doc_1"]


def test_resolve_latest_fallback_when_no_time() -> None:
    driver = FakeDriver(
        {
            queries.RESOLVE_LATEST_DOCUMENTS_QUERY: [
                {"doc_id": "doc_latest", "timestamp": "2024-12-31"}
            ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = TimeContext(raw_text="latest", mode="latest_fallback", needs_fallback=True)
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["doc_latest"]
    assert result.fallback_used is True


def test_resolve_missing_collection_raises_explicit_error() -> None:
    resolver = DocumentResolver(driver=FakeDriver({}))
    with pytest.raises(ValueError, match="collection is required"):
        resolver.resolve("", TimeContext(raw_text="Q1 FY24", mode="quarter"))


def test_tie_ordering_stability_by_doc_id_is_delegated_to_query_order() -> None:
    driver = FakeDriver(
        {
            queries.RESOLVE_DOCUMENTS_BY_FISCAL_YEAR_QUERY: [
                {"doc_id": "doc_a", "timestamp": "2024-04-30"},
                {"doc_id": "doc_b", "timestamp": "2024-04-30"},
            ]
        }
    )
    resolver = DocumentResolver(driver=driver)
    context = TimeContext(raw_text="FY24", mode="year", fiscal_year="FY2024")
    result = resolver.resolve("RELIANCE", context)
    assert result.doc_ids == ["doc_a", "doc_b"]
