from __future__ import annotations

from dataclasses import dataclass

from raqe.collection_namespace import to_external, to_internal
from raqe.graph.neo4j_client import get_driver
from raqe.graph.queries import (
    UPSERT_CHUNK_QUERY,
    UPSERT_COLLECTION_QUERY,
    UPSERT_DOCUMENT_QUERY,
    UPSERT_REFERENCE_TARGET_AND_LINK_QUERY,
    UPSERT_SECTION_AND_LINK_CHUNK_QUERY,
)
from raqe.ingestion.chunk_ingestor import map_chunkitem_to_raqe
from raqe.models.ingestion import DocumentIngestionPayload


@dataclass
class IngestionResult:
    collection_id: str
    document_id: str
    chunk_count: int
    section_count: int
    reference_count: int


class DocumentIngestor:
    def __init__(self, driver=None):
        self.driver = driver or get_driver()

    def ingest_document(self, payload: DocumentIngestionPayload) -> IngestionResult:
        section_ids: set[str] = set()
        reference_count = 0
        internal_collection_id = to_internal(payload.collection_id) or payload.collection_id
        payload_write = payload.model_copy(update={"collection_id": internal_collection_id})

        with self.driver.session() as session:
            session.execute_write(self._upsert_collection, internal_collection_id)
            session.execute_write(self._upsert_document, payload_write)

            for chunk in payload.chunks:
                normalized = map_chunkitem_to_raqe(chunk, internal_collection_id, payload.timestamp)
                session.execute_write(self._upsert_chunk, normalized.model_dump())

                if normalized.section_id and normalized.section_label:
                    section_ids.add(normalized.section_id)
                    session.execute_write(self._upsert_section, normalized.model_dump())

                for reference in normalized.references:
                    reference_count += 1
                    session.execute_write(
                        self._upsert_reference,
                        normalized.chunk_id,
                        normalized.collection_id,
                        normalized.document_id,
                        reference.model_dump(),
                    )

        return IngestionResult(
            collection_id=to_external(internal_collection_id) or payload.collection_id,
            document_id=payload.doc_id,
            chunk_count=len(payload.chunks),
            section_count=len(section_ids),
            reference_count=reference_count,
        )

    @staticmethod
    def _upsert_collection(tx, collection_id: str) -> None:
        tx.run(UPSERT_COLLECTION_QUERY, collection_id=collection_id)

    @staticmethod
    def _upsert_document(tx, payload: DocumentIngestionPayload) -> None:
        tx.run(
            UPSERT_DOCUMENT_QUERY,
            collection_id=payload.collection_id,
            document_id=payload.doc_id,
            fiscal_year=payload.fiscal_year,
            period=payload.period,
            timestamp=payload.timestamp,
        )

    @staticmethod
    def _upsert_chunk(tx, chunk: dict) -> None:
        tx.run(UPSERT_CHUNK_QUERY, **chunk)

    @staticmethod
    def _upsert_section(tx, chunk: dict) -> None:
        tx.run(
            UPSERT_SECTION_AND_LINK_CHUNK_QUERY,
            collection_id=chunk["collection_id"],
            document_id=chunk["document_id"],
            chunk_id=chunk["chunk_id"],
            section_id=chunk["section_id"],
            section_label=chunk["section_label"],
            section_title=chunk["section_title"],
        )

    @staticmethod
    def _upsert_reference(
        tx,
        chunk_id: str,
        collection_id: str,
        document_id: str,
        reference: dict,
    ) -> None:
        tx.run(
            UPSERT_REFERENCE_TARGET_AND_LINK_QUERY,
            chunk_id=chunk_id,
            collection_id=collection_id,
            document_id=document_id,
            reference_text=reference["reference_text"],
            reference_type=reference["reference_type"],
            target_label=reference["target_label"],
            confidence=reference["confidence"],
        )
