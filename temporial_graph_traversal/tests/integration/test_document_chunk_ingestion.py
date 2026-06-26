from raqe.ingestion.document_ingestor import DocumentIngestor
from raqe.models.ingestion import ChunkItem, ChunkReferenceItem, DocumentIngestionPayload


class FakeTx:
    def __init__(self, calls: list[tuple[str, dict]]) -> None:
        self.calls = calls

    def run(self, query: str, **params) -> None:
        self.calls.append((query, params))


class FakeSession:
    def __init__(self, calls: list[tuple[str, dict]]) -> None:
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute_write(self, fn, *args):
        tx = FakeTx(self.calls)
        return fn(tx, *args)


class FakeDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def session(self):
        return FakeSession(self.calls)


def test_document_ingestion_persists_collection_document_chunks_sections_and_references() -> None:
    payload = DocumentIngestionPayload(
        collection_id="RELIANCE",
        doc_id="doc_q1_fy24",
        fiscal_year="FY24",
        period="Q1",
        timestamp="2024-04-30",
        chunks=[
            ChunkItem(
                chunk_id="ch_1",
                content="Section 4.2 mentions Table 3",
                type="TEXT",
                doc_id="doc_q1_fy24",
                page=5,
                bundle_id="bundle_q1",
                section_title="4.2 Revenue",
                title_summary="Revenue summary",
                publish_date="2024-04-30",
                prev_chunk=None,
                next_chunk="ch_2",
                references=[
                    ChunkReferenceItem(
                        reference_text="Table 3",
                        reference_type="TABLE",
                        target_label="3",
                        confidence=0.96,
                    )
                ],
            ),
            ChunkItem(
                chunk_id="ch_2",
                content="Section 5 notes margin expansion",
                type="TEXT",
                doc_id="doc_q1_fy24",
                page=6,
                bundle_id="bundle_q1",
                section_title="5 Margin",
                title_summary="Margin summary",
                publish_date=None,
                prev_chunk="ch_1",
                next_chunk=None,
                references=[],
            ),
        ],
    )

    driver = FakeDriver()
    ingestor = DocumentIngestor(driver=driver)
    result = ingestor.ingest_document(payload)

    assert result.collection_id == "RELIANCE"
    assert result.document_id == "doc_q1_fy24"
    assert result.chunk_count == 2
    assert result.section_count == 2
    assert result.reference_count == 1

    chunk_calls = [params for _, params in driver.calls if "chunk_id" in params and "chunk_type" in params]
    assert {c["chunk_id"] for c in chunk_calls} == {"ch_1", "ch_2"}
    assert all(c["collection_id"] == "tgt_graph_RELIANCE" for c in chunk_calls)
    assert all(c["document_id"] == "doc_q1_fy24" for c in chunk_calls)

    section_calls = [params for _, params in driver.calls if "section_id" in params]
    assert {s["section_id"] for s in section_calls} == {"sec_4.2", "sec_5"}

    reference_calls = [params for _, params in driver.calls if "reference_text" in params]
    assert len(reference_calls) == 1
    assert reference_calls[0]["target_label"] == "3"
    assert reference_calls[0]["confidence"] == 0.96
