from raqe.ingestion.chunk_ingestor import (
    map_chunkitem_to_raqe,
    normalize_timestamp,
    parse_section_identity,
)
from raqe.models.ingestion import ChunkItem, ChunkReferenceItem


def test_parse_section_identity_extracts_numeric_label() -> None:
    label, section_id = parse_section_identity("Section 4.2 Revenue Growth")
    assert label == "4.2"
    assert section_id == "sec_4.2"


def test_parse_section_identity_handles_missing_label() -> None:
    label, section_id = parse_section_identity("Business Overview")
    assert label is None
    assert section_id is None


def test_normalize_timestamp_falls_back_for_invalid_date() -> None:
    assert normalize_timestamp("not-a-date", "2024-03-31") == "2024-03-31"


def test_map_chunkitem_to_raqe_preserves_references_and_derives_fields() -> None:
    chunk = ChunkItem(
        chunk_id="ch_1",
        content="Revenue grew, see Table 3",
        type="TEXT",
        doc_id="doc_1",
        page=4,
        bundle_id="bundle_1",
        section_title="4.2 Revenue",
        title_summary="Revenue section",
        publish_date="2024-04-30",
        prev_chunk=None,
        next_chunk="ch_2",
        references=[
            ChunkReferenceItem(
                reference_text="Table 3",
                reference_type="TABLE",
                target_label="3",
                confidence=0.95,
            )
        ],
    )
    normalized = map_chunkitem_to_raqe(
        chunk=chunk,
        collection_id="RELIANCE",
        document_timestamp="2024-03-31",
    )

    assert normalized.collection_id == "RELIANCE"
    assert normalized.document_id == "doc_1"
    assert normalized.section_label == "4.2"
    assert normalized.section_id == "sec_4.2"
    assert normalized.timestamp == "2024-04-30"
    assert len(normalized.references) == 1
    assert normalized.references[0].target_label == "3"
