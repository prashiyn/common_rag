from __future__ import annotations

from raqe.collection_namespace import to_internal
from raqe.graph.neo4j_client import get_driver
from raqe.graph.queries import (
    RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY,
    RESOLVE_DOCUMENTS_BY_FISCAL_YEAR_QUERY,
    RESOLVE_DOCUMENTS_BY_QUARTER_QUERY,
    RESOLVE_LATEST_DOCUMENTS_QUERY,
)
from raqe.models.time_context import DocumentResolutionResult, TimeContext


class DocumentResolver:
    def __init__(self, driver=None):
        self.driver = driver or get_driver()

    def resolve(self, collection: str, time_context: TimeContext) -> DocumentResolutionResult:
        if not collection:
            raise ValueError("collection is required")
        collection = to_internal(collection) or collection

        mode = time_context.mode
        with self.driver.session() as session:
            if mode == "quarter" and time_context.period and time_context.fiscal_year:
                records = session.run(
                    RESOLVE_DOCUMENTS_BY_QUARTER_QUERY,
                    collection_id=collection,
                    period=time_context.period,
                    fiscal_year=time_context.fiscal_year,
                )
                return self._build_result(
                    collection,
                    records,
                    mode_used="quarter",
                    fallback=False,
                    reason="resolved by quarter and fiscal year",
                )

            if mode == "year" and time_context.fiscal_year:
                records = session.run(
                    RESOLVE_DOCUMENTS_BY_FISCAL_YEAR_QUERY,
                    collection_id=collection,
                    fiscal_year=time_context.fiscal_year,
                )
                return self._build_result(
                    collection,
                    records,
                    mode_used="year",
                    fallback=False,
                    reason="resolved by fiscal year",
                )

            if mode == "explicit_range" and time_context.start_date and time_context.end_date:
                records = session.run(
                    RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY,
                    collection_id=collection,
                    start_date=time_context.start_date,
                    end_date=time_context.end_date,
                )
                return self._build_result(
                    collection,
                    records,
                    mode_used="explicit_range",
                    fallback=False,
                    reason="resolved by explicit date range",
                )

            records = session.run(
                RESOLVE_LATEST_DOCUMENTS_QUERY,
                collection_id=collection,
            )
            return self._build_result(
                collection,
                records,
                mode_used="latest_fallback",
                fallback=True,
                reason="fallback to latest documents",
            )

    @staticmethod
    def _build_result(
        collection_id: str,
        records,
        mode_used: str,
        fallback: bool,
        reason: str,
    ) -> DocumentResolutionResult:
        doc_ids = [record["doc_id"] for record in records]
        return DocumentResolutionResult(
            collection_id=collection_id,
            doc_ids=doc_ids,
            mode_used=mode_used,
            fallback_used=fallback,
            reason=reason,
        )


def resolve_documents(collection: str, time_context: TimeContext, driver=None) -> list[str]:
    resolver = DocumentResolver(driver=driver)
    return resolver.resolve(collection, time_context).doc_ids
