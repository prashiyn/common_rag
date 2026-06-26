# Phase 1 Comprehensive Implementation Guide

## RAQE Phase 1 - Graph Data Model + Ingestion Contract

This document is the execution guide for Phase 1 implementation. It is written for both:

- Human developers
- Cursor agents executing scoped coding tasks

---

## 1) Phase 1 Objective

Implement a robust ingestion foundation where:

1. Canonical chunk input strictly follows `ChunkItem` schema from `docs/doc_processing_openapi.json`.
2. Each document in a collection owns a list of chunks:
   - `Collection -> Document -> [Chunks]`
3. Canonical chunk fields are mapped to RAQE-normalized fields required for graph reasoning.
4. References are preserved and stored for later traversal/disambiguation.

---

## 2) Golden Truth Schema (Must Follow)

Use `ChunkItem` as canonical raw input.

### Required `ChunkItem` fields

- `chunk_id: str`
- `content: str`
- `type: str`
- `doc_id: str`
- `page: int | null`
- `bundle_id: str`
- `section_title: str | null`
- `title_summary: str`
- `publish_date: str | null`
- `prev_chunk: str | null`
- `next_chunk: str | null`

### `references` field

- Optional array of `ChunkReferenceItem`
- If present, each reference requires:
  - `reference_text: str`
  - `reference_type: str`
  - `target_label: str`
  - `confidence: float (0..1)`

No Phase 1 implementation should redefine these canonical fields.

---

## 3) Phase 1 Scope Boundaries

Included:

- Input models and validators
- Canonical-to-RAQE mapping layer
- Ingestion/upsert contract for graph lineage
- Unit/integration tests for ingestion correctness

Not included:

- Temporal query interpretation logic (`parse_time`, resolver ranking)
- End-to-end query answering
- Backtesting

---

## 4) Target File Plan

Create/update the following files in Phase 1:

- `app/models/ingestion.py`
- `app/models/graph_entities.py`
- `app/ingestion/document_ingestor.py`
- `app/ingestion/chunk_ingestor.py`
- `app/graph/queries.py`
- `tests/unit/test_ingestion_models.py`
- `tests/unit/test_chunk_mapping.py`
- `tests/integration/test_document_chunk_ingestion.py`

If file naming differs slightly in repo, preserve intent and structure.

---

## 5) Data Contracts to Implement

## 5.1 Canonical Models

Implement canonical models that mirror OpenAPI:

- `ChunkReferenceItem`
- `ChunkItem`

These models should preserve nullable semantics exactly.

## 5.2 Document Payload Model

Implement a collection-scoped document payload:

```json
{
  "collection_id": "RELIANCE",
  "doc_id": "doc_1",
  "fiscal_year": "FY24",
  "period": "Q1",
  "timestamp": "2024-04-30",
  "chunks": [ { "ChunkItem": "..." } ]
}
```

`chunks` must be non-empty for accepted ingestion.

## 5.3 RAQE Normalized Chunk Model

Define a normalized chunk representation used internally after mapping:

- canonical fields retained where needed (`chunk_id`, `doc_id`, `content`, `references`, etc.)
- enriched fields:
  - `collection_id`
  - normalized `document_id`
  - normalized temporal metadata (`timestamp`, and placeholders for `period`, `fiscal_year` if needed)
  - section identity derived from `section_title` (`section_label` and/or synthetic `section_id`)

---

## 6) Canonical-to-RAQE Mapping Rules

Implement `map_chunkitem_to_raqe(chunk, collection_id, document_metadata)`.

Required mapping behavior:

1. `doc_id` -> internal `document_id`
2. `publish_date` -> normalized timestamp when present
3. `section_title`:
   - keep original text
   - derive normalized section label/id if parseable
4. `references`:
   - preserve all canonical fields unchanged
   - store confidence as numeric float
5. preserve adjacency:
   - `prev_chunk`, `next_chunk` retained for sequence/proximity use

Mapping must be deterministic and side-effect free.

---

## 7) Graph Upsert Contract

Ensure ingestion produces/updates:

1. `(:Collection {id/name})`
2. `(:Document {id, collection_id, fiscal_year, period, timestamp})`
3. `(:Chunk {id, document_id, collection_id, ...})`
4. `(:Section {id/label, document_id, collection_id})` where derivable
5. relationships:
   - `(Collection)-[:HAS_DOCUMENT]->(Document)`
   - `(Document)-[:HAS_CHUNK]->(Chunk)`
   - `(Chunk)-[:IN_SECTION]->(Section)` (when section derivation exists)
   - reference edges via section/ref workflow chosen by your schema

All upserts must be idempotent.

---

## 8) Validation and Error Policy

Reject input when:

- required canonical `ChunkItem` fields are missing
- `chunks` list is empty
- `doc_id` in chunk conflicts with parent document id
- `collection_id` missing at document payload level

Accept nullable canonical fields (`page`, `section_title`, `publish_date`, `prev_chunk`, `next_chunk`) per OpenAPI.

Return structured validation errors with actionable messages.

---

## 9) Test Plan (Mandatory)

## Unit Tests

1. Canonical model validation:
   - valid `ChunkItem`
   - invalid missing required field
2. Mapping tests:
   - publish date normalization
   - section title parsing fallback
   - references preserved exactly
3. Consistency checks:
   - chunk `doc_id` mismatch rejection

## Integration Tests

1. Ingest one document with multiple chunks.
2. Verify graph lineage:
   - collection exists
   - document linked to collection
   - all chunks linked to document
3. Verify references persisted and queryable.
4. Negative test:
   - no chunk linked to wrong document/collection.

---

## 10) Cursor Agent Execution Packets

Use one packet per task.

### Packet A - Models

```text
Task: Implement canonical and normalized ingestion models
Files: app/models/ingestion.py, app/models/graph_entities.py
Must preserve:
- ChunkItem parity with OpenAPI schema
- Document -> chunks contract
Done when:
- unit model validation tests pass
```

### Packet B - Mapping Layer

```text
Task: Implement canonical-to-RAQE chunk mapping
Files: app/ingestion/chunk_ingestor.py
Must preserve:
- deterministic mapping
- references intact
- doc/collection lineage fields populated
Done when:
- mapping tests pass for null and non-null fields
```

### Packet C - Graph Upsert

```text
Task: Implement document/chunk graph upsert flow
Files: app/ingestion/document_ingestor.py, app/graph/queries.py
Must preserve:
- Collection -> Document -> Chunk lineage
- idempotent writes
Done when:
- integration ingestion tests pass
```

### Packet D - Validation + Negative Paths

```text
Task: Implement ingestion validation and error responses
Files: ingestion modules + tests
Must preserve:
- strict required canonical fields
- empty chunk list rejection
- doc_id mismatch rejection
Done when:
- negative tests pass with clear error payloads
```

---

## 11) Phase 1 Definition of Done

Phase 1 is complete only when all are true:

1. Canonical `ChunkItem` is implemented as the source-of-truth input model.
2. Document payload with `chunks[]` is validated and ingested.
3. `Collection -> Document -> Chunk` lineage is persisted and test-verified.
4. Canonical-to-RAQE mapping is deterministic and tested.
5. Reference payloads are preserved for downstream resolver phases.
6. Negative tests confirm no cross-document/cross-collection leakage.
