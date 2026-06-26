import pytest
from pydantic import ValidationError

from raqe.models.ingestion import ChunkItem, ChunkReferenceItem, DocumentIngestionPayload


def test_chunkitem_accepts_nullable_required_fields() -> None:
    chunk = ChunkItem(
        chunk_id="ch_1",
        content="content",
        type="TEXT",
        doc_id="doc_1",
        page=None,
        bundle_id="bundle_1",
        section_title=None,
        title_summary="summary",
        publish_date=None,
        prev_chunk=None,
        next_chunk=None,
    )
    assert chunk.chunk_id == "ch_1"
    assert chunk.page is None


def test_chunk_reference_confidence_must_be_bounded() -> None:
    with pytest.raises(ValidationError):
        ChunkReferenceItem(
            reference_text="Table 9",
            reference_type="TABLE",
            target_label="9",
            confidence=1.2,
        )


def test_document_payload_rejects_empty_chunks() -> None:
    with pytest.raises(ValidationError):
        DocumentIngestionPayload(
            collection_id="RELIANCE",
            doc_id="doc_1",
            fiscal_year="FY24",
            period="Q1",
            timestamp="2024-04-30",
            chunks=[],
        )


def test_document_payload_rejects_mismatched_chunk_doc_id() -> None:
    with pytest.raises(ValidationError):
        DocumentIngestionPayload(
            collection_id="RELIANCE",
            doc_id="doc_1",
            fiscal_year="FY24",
            period="Q1",
            timestamp="2024-04-30",
            chunks=[
                ChunkItem(
                    chunk_id="ch_1",
                    content="content",
                    type="TEXT",
                    doc_id="doc_2",
                    page=1,
                    bundle_id="bundle_1",
                    section_title="4.2 Revenue",
                    title_summary="summary",
                    publish_date="2024-04-30",
                    prev_chunk=None,
                    next_chunk=None,
                )
            ],
        )
