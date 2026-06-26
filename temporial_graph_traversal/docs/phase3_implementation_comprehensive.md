# Phase 3 Comprehensive Implementation Guide

## RAQE Phase 3 - Document Chunk Loading + Chunk Filtering Layer

This document is the execution guide for Phase 3 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 3 Objective

Implement a strict chunk retrieval layer that:

1. Loads chunks only from documents resolved in Phase 2.
2. Preserves `Collection -> Document -> [Chunks]` ownership.
3. Filters/ranks chunks for downstream graph traversal and disambiguation.
4. Prevents cross-collection and cross-document leakage by construction.

---

## 2) Inputs and Dependencies

Phase 3 depends on:

- Phase 1 ingestion and graph lineage (`Collection -> Document -> Chunk`)
- Phase 2 deterministic document resolver (`resolve_documents`)

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`
- `docs/phase1_implementation_comprehensive.md`
- `docs/phase2_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Document chunk loader (`load_document_chunks`)
- Chunk filtering service (`filter_chunks`)
- Optional section/target-aware narrowing
- Deterministic ordering/ranking and metadata-rich output
- Unit + integration tests for chunk retrieval correctness

Not included:

- Reference resolution/disambiguation (Phase 4)
- Multi-hop reference traversal expansion logic (Phase 5)
- Answer generation changes

---

## 4) Target File Plan

Create/update these files:

- `app/agent/document_chunk_loader.py` (create)
- `app/agent/chunk_filter.py` (create)
- `app/agent/executor.py` (update to integrate loader/filter)
- `app/graph/queries.py` (add chunk retrieval queries)
- `app/models/chunk_filtering.py` (create)
- `tests/unit/test_document_chunk_loader.py` (create)
- `tests/unit/test_chunk_filter.py` (create)
- `tests/integration/test_chunk_filtering_pipeline.py` (create)

Optional helper (if scoring grows):

- `app/agent/chunk_scoring.py` (create)

---

## 5) Functional Requirements

## 5.1 `load_document_chunks(collection, doc_ids) -> dict[str, list[dict]]`

Behavior:

1. Require `collection` and non-empty `doc_ids`.
2. Query only chunks whose `document_id` is in `doc_ids` and `collection_id` matches.
3. Return dictionary keyed by `document_id`.
4. Preserve deterministic ordering (primary: `timestamp` desc, secondary: `chunk_id` asc).
5. Return empty dict for empty inputs; never widen scope.

## 5.2 `filter_chunks(collection, doc_ids, target=None, section_hint=None) -> list[dict]`

Behavior:

1. Load chunks only via `load_document_chunks`.
2. Apply optional narrowing:
   - `target` keyword relevance against `content` + `title_summary`
   - `section_hint` match against `section_title` / `section_label`
3. Attach filtering metadata:
   - `collection_id`, `document_id`, `chunk_id`
   - `match_reasons` (list)
   - `score` (deterministic numeric)
4. Sort deterministically by:
   - score desc
   - timestamp desc
   - chunk_id asc
5. Return only chunks from provided documents.

---

## 6) Output Contract

Define a filtered chunk output model (recommended in `app/models/chunk_filtering.py`):

```python
class FilteredChunk(BaseModel):
    collection_id: str
    document_id: str
    chunk_id: str
    content: str
    title_summary: str
    section_title: str | None
    section_label: str | None
    timestamp: str
    references: list[dict]
    score: float
    match_reasons: list[str]
```

This output should be directly usable by Phase 4 resolver and Phase 5 executor.

---

## 7) Query Contract (Neo4j)

Add chunk retrieval query templates to `app/graph/queries.py`:

1. `LOAD_CHUNKS_FOR_DOC_IDS_QUERY`
2. Optional targeted query for section prefilter:
   - `LOAD_CHUNKS_FOR_DOC_IDS_WITH_SECTION_HINT_QUERY`

All queries must:

- start from collection scope
- enforce `d.id IN $doc_ids`
- enforce chunk ownership under matched documents
- return stable ordering

Example shape:

```cypher
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)-[:HAS_CHUNK]->(ch:Chunk)
WHERE d.id IN $doc_ids
  AND ch.collection_id = $collection_id
RETURN d.id AS document_id, ch
ORDER BY ch.timestamp DESC, ch.id ASC
```

---

## 8) Filtering and Scoring Rules

Use deterministic scoring (no model calls in Phase 3):

Base scoring suggestion:

- +3.0 if `target` token appears in chunk `content`
- +2.0 if `target` appears in `title_summary`
- +1.5 if `section_hint` appears in `section_title`
- +1.0 if chunk contains references

Additional constraints:

- Normalize text to lowercase for matching.
- Token matching should ignore punctuation.
- If no `target` and no `section_hint`, still return scoped chunks ordered by recency.

---

## 9) Error and Edge-Case Policy

Expected behavior:

- Missing collection -> `ValueError("collection is required")`
- Empty `doc_ids` -> return empty output, not exception
- Unknown `doc_ids` -> return empty output
- Missing optional chunk fields -> tolerate and continue

Never:

- Query chunks outside provided `doc_ids`
- Auto-expand to all documents in collection
- Auto-expand to other collections

---

## 10) Executor Integration

Update `app/agent/executor.py` so the Phase 3 flow is:

1. Resolve documents (Phase 2)
2. Load scoped document chunks
3. Filter/rank chunks based on query target/hints
4. Pass filtered chunks to downstream stages (`fetch_events`, `traverse_references`, ...)

`execute_plan` should include filtered chunk metadata in its returned payload.

---

## 11) Test Plan (Comprehensive)

## 11.1 Unit: `test_document_chunk_loader.py`

Cover:

1. Loader enforces collection/doc scope in query params.
2. Loader groups rows by document ID.
3. Loader returns empty dict for empty doc list.
4. Loader never returns chunks from non-requested docs.

## 11.2 Unit: `test_chunk_filter.py`

Cover:

1. Content target match scoring.
2. Title summary target match scoring.
3. Section hint scoring.
4. Deterministic tie ordering.
5. No target/hint returns recency-ordered scoped chunks.
6. Score metadata + match reasons are present.

## 11.3 Integration: `test_chunk_filtering_pipeline.py`

Integration scenarios:

1. Collection with multiple docs and overlapping chunk topics.
2. Filter query returns chunks only for resolver doc IDs.
3. Cross-collection negative case confirms zero leakage.
4. Invalid/non-existent doc IDs return empty list.
5. Executor integration path includes filtered chunks in output.

---

## 12) Cursor Agent Execution Packets

### Packet A - Loader

```text
Task: Implement scoped document chunk loader
Files: app/agent/document_chunk_loader.py, app/graph/queries.py
Must preserve:
- collection-first + doc_ids-scoped query
- deterministic output grouping/order
Done when:
- loader unit tests pass
```

### Packet B - Filter + Scoring

```text
Task: Implement deterministic chunk filter and scoring
Files: app/agent/chunk_filter.py, app/models/chunk_filtering.py
Must preserve:
- no cross-document leakage
- deterministic scoring and ordering
- structured match reasons
Done when:
- chunk filter unit tests pass
```

### Packet C - Executor Wiring + Integration

```text
Task: Wire loader/filter into executor and add integration coverage
Files: app/agent/executor.py, tests/integration/test_chunk_filtering_pipeline.py
Must preserve:
- phase order: resolve docs -> load chunks -> filter chunks
- filtered chunk metadata included in execution output
Done when:
- integration tests pass
```

---

## 13) Implementation Checklist

- [ ] `load_document_chunks` implemented with strict scope
- [ ] `filter_chunks` implemented with deterministic scoring/order
- [ ] Structured filtered chunk model added
- [ ] Neo4j chunk queries scoped and stable
- [ ] Executor flow updated to include loader/filter stage
- [ ] Unit + integration tests added for positive and negative paths

---

## 14) Phase 3 Definition of Done

Phase 3 is complete only when:

1. Chunk retrieval is strictly bounded to `(collection, doc_ids)`.
2. Filtered chunks include consistent scoring and match reason metadata.
3. Deterministic ordering is preserved across repeated runs.
4. Executor output is chunk-filter aware for downstream phases.
5. Cross-collection/cross-document leakage is prevented and test-verified.
