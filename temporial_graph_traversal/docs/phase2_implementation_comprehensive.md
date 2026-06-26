# Phase 2 Comprehensive Implementation Guide

## RAQE Phase 2 - Temporal Parsing + Collection-Scoped Document Resolution

This document is the execution guide for Phase 2 implementation. It is designed for:

- Human developers
- Cursor agents executing bounded implementation tasks

---

## 1) Phase 2 Objective

Implement deterministic temporal reasoning that converts user query time context into a scoped, ordered set of document IDs inside a single collection.

Phase 2 must guarantee:

1. Time context is parsed consistently from natural language.
2. Document resolution always starts from `collection_id`.
3. Returned `doc_ids` are deterministic, ordered, and explainable.
4. Ambiguous/no-time queries fall back safely to latest document scope.

---

## 2) Inputs and Dependencies

Phase 2 depends on Phase 1 contracts:

- Canonical chunk/document ingestion is implemented.
- `Collection -> Document -> Chunk` lineage exists.
- Document metadata includes `timestamp`, `period`, `fiscal_year`.

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`
- `docs/phase1_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Query time parsing (`parse_time`)
- Time-context model
- Collection-scoped document resolver (`resolve_documents`)
- Deterministic sorting and fallback policy
- Unit + integration tests for resolver behavior

Not included:

- Chunk filtering and traversal (Phase 3+)
- Reference disambiguation logic (Phase 4)
- End-to-end answer generation changes

---

## 4) Target File Plan

Create/update these files:

- `app/agent/parser.py` (update)
- `app/agent/time_resolver.py` (create)
- `app/agent/document_resolver.py` (create)
- `app/graph/queries.py` (update with resolver queries)
- `app/models/time_context.py` (create)
- `tests/unit/test_time_resolver.py` (create)
- `tests/unit/test_document_resolver.py` (create)
- `tests/integration/test_temporal_document_resolution.py` (create)

Optional (if needed for shared sorting logic):

- `app/agent/resolution_utils.py` (create)

---

## 5) Functional Requirements

## 5.1 `parse_time(question: str) -> TimeContext`

The parser should recognize these classes:

1. **Explicit date range**
   - Example: "between 2023-04-01 and 2024-03-31"
2. **Quarter expressions**
   - "Q1 FY24", "FY24 Q1", "last quarter"
3. **Year expressions**
   - "FY24", "financial year 2024", "2024"
4. **Relative windows**
   - "latest", "recent", "last N quarters", "last year"
5. **No explicit time**
   - should produce a valid context with fallback mode enabled

`TimeContext` should include:

- `raw_text`
- `mode` (enum-like: `explicit_range`, `quarter`, `year`, `relative`, `latest_fallback`)
- optional `start_date`, `end_date`
- optional `period`, `fiscal_year`
- optional `relative_window`
- `needs_fallback` boolean

## 5.2 `resolve_documents(collection, time_context) -> list[str]`

Resolver rules:

1. Filter by collection first.
2. Apply time constraints based on context mode.
3. Sort deterministically:
   - primary: latest timestamp descending
   - secondary: stable key (document ID ascending) for ties
4. Return ordered list of `doc_ids`.
5. If no explicit time or ambiguous context:
   - return latest document set under same collection.

## 5.3 Deterministic Fallback Policy

Fallback should never cross collections.

Required fallback behavior:

- If parsing fails to extract usable time constraints:
  - mark `needs_fallback=True`
  - return latest scoped docs for the collection
- If time constraints produce no documents:
  - return empty list (do not silently widen scope), plus reason metadata in resolver result helper

---

## 6) Data Contracts

## 6.1 TimeContext model

Recommended fields:

```python
class TimeContext(BaseModel):
    raw_text: str
    mode: str
    start_date: str | None = None
    end_date: str | None = None
    period: str | None = None
    fiscal_year: str | None = None
    relative_window: str | None = None
    needs_fallback: bool = False
```

## 6.2 Resolver Output

Use a helper return model for observability:

```python
class DocumentResolutionResult(BaseModel):
    collection_id: str
    doc_ids: list[str]
    mode_used: str
    fallback_used: bool
    reason: str
```

Then expose `doc_ids` directly where existing interfaces expect list output.

---

## 7) Query Contract (Neo4j)

Add resolver-specific query templates to `app/graph/queries.py`:

1. **By quarter + fiscal year**
2. **By fiscal year only**
3. **By date range**
4. **Latest documents for collection**

All queries must:

- start from `Collection`
- constrain `Document.collection_id`
- return deterministic ordering

Example shape:

```cypher
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.collection_id = $collection_id
RETURN d.id AS doc_id, d.timestamp AS timestamp
ORDER BY d.timestamp DESC, d.id ASC
```

---

## 8) Parsing Rules (Practical)

Implement parser using explicit regex/token patterns first (deterministic and testable).

Minimum patterns:

- `Q[1-4]\s*FY\d{2,4}`
- `FY\d{2,4}`
- ISO date `YYYY-MM-DD`
- phrases: `last quarter`, `last year`, `latest`, `recent`

Normalization guidance:

- Normalize `FY24` and `FY2024` to one internal format (pick one and stay consistent).
- Normalize quarter labels to `Q1..Q4`.
- Convert relative windows using current date injected via helper for testability.

---

## 9) Error Handling Policy

Phase 2 should not raise generic exceptions for common parse ambiguity.

Expected behavior:

- unknown time text -> `latest_fallback`
- malformed explicit dates -> deterministic parse failure path with `needs_fallback=True`
- missing collection in resolver input -> raise explicit `ValueError("collection is required")`

---

## 10) Test Plan (Comprehensive)

## 10.1 Unit: `test_time_resolver.py`

Cover at least:

1. Parse "Q1 FY24" -> quarter mode + normalized fields.
2. Parse "between 2024-01-01 and 2024-03-31" -> explicit range.
3. Parse "last quarter" -> relative mode.
4. Parse "latest results" -> latest fallback mode.
5. Invalid date text -> fallback context, not crash.

## 10.2 Unit: `test_document_resolver.py`

Use fake driver/session/tx patterns (similar to Phase 1 integration style):

1. Collection + quarter/year query returns expected ordered doc IDs.
2. Date range query returns deterministic order.
3. No-time context returns latest docs for collection.
4. Missing collection raises explicit error.
5. Tie ordering uses doc ID secondary key.

## 10.3 Integration: `test_temporal_document_resolution.py`

Integration-focused scenarios:

1. Collection with multiple quarterly docs across years.
2. Query "Q1 FY24" returns only matching docs.
3. Query "latest" returns newest scoped docs.
4. Query with non-matching range returns empty list without widening scope.
5. Negative test: same doc labels in another collection are not returned.

---

## 11) Cursor Agent Execution Packets

### Packet A - Time Context Model + Parser

```text
Task: Implement TimeContext model and parse_time
Files: app/models/time_context.py, app/agent/time_resolver.py, app/agent/parser.py
Must preserve:
- deterministic parsing
- explicit fallback mode
- no collection widening logic here
Done when:
- all time parser unit tests pass
```

### Packet B - Document Resolver + Queries

```text
Task: Implement collection-scoped resolve_documents with mode-based query routing
Files: app/agent/document_resolver.py, app/graph/queries.py
Must preserve:
- collection-first filtering
- deterministic ordering
- latest fallback only within same collection
Done when:
- resolver unit tests pass
```

### Packet C - Integration Coverage

```text
Task: Add temporal resolution integration tests
Files: tests/integration/test_temporal_document_resolution.py
Must preserve:
- cross-collection isolation assertions
- empty-result behavior for non-matching ranges
Done when:
- integration tests pass
```

---

## 12) Implementation Checklist

- [ ] `parse_time` supports quarter/year/date-range/relative/latest patterns
- [ ] `TimeContext` model added and used consistently
- [ ] `resolve_documents` enforces `collection` as mandatory input
- [ ] Resolver queries are collection-scoped and ordered deterministically
- [ ] Fallback behavior is explicit and test-validated
- [ ] Unit and integration tests cover positive + negative paths

---

## 13) Phase 2 Definition of Done

Phase 2 is complete only when:

1. Time context parsing is deterministic and fully test-covered.
2. Document resolution is always collection-scoped.
3. Returned document IDs are deterministic in order.
4. Ambiguous/no-time queries use latest fallback within the same collection.
5. Non-matching explicit time constraints return empty scoped results (no widening).
6. Cross-collection leakage is prevented and covered by tests.
