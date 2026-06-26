# Phase 4 Comprehensive Implementation Guide

## RAQE Phase 4 - Reference Resolution + Disambiguation

This document is the execution guide for Phase 4 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 4 Objective

Implement deterministic reference resolution that converts extracted references (for example, `Table 3`) into scoped, auditable target selections.

Phase 4 must guarantee:

1. Resolution is bounded by `collection_id` and resolved `doc_ids`.
2. Label matching is normalized (`Table 3` -> `3`).
3. Ambiguous candidates are ranked by explicit disambiguation rules.
4. Resolver outputs include trace metadata explaining why a target was selected.

---

## 2) Inputs and Dependencies

Phase 4 depends on:

- Phase 1 ingestion contracts (`references[]` on chunks)
- Phase 2 document scoping (`resolve_documents`)
- Phase 3 filtered chunk output (`filtered_chunks`)

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`
- `docs/phase3_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Reference normalization utilities
- `resolve_reference` and batch traversal for filtered chunks
- Disambiguation scoring/ranking
- Resolver trace metadata
- Unit + integration tests for ambiguity and scope isolation

Not included:

- Multi-hop traversal expansion depth tuning (Phase 5)
- Final answer rendering changes

---

## 4) Target File Plan

Create/update these files:

- `app/structure/disambiguator.py` (create)
- `app/structure/resolver.py` (replace placeholder with full resolver)
- `app/agent/executor.py` (wire resolver into `traverse_references`)
- `app/models/reference_resolution.py` (create)
- `app/graph/queries.py` (optional scoped candidate query constants)
- `tests/unit/test_disambiguator.py` (create)
- `tests/unit/test_reference_resolver.py` (create)
- `tests/integration/test_reference_resolution_pipeline.py` (create)

---

## 5) Functional Requirements

## 5.1 `normalize_reference_label(ref_text, target_label) -> str`

Requirements:

- Prefer explicit `target_label` when present.
- Otherwise parse numeric/alphanumeric suffix from reference text.
- Normalize casing/whitespace.

## 5.2 `resolve_reference(ref, collection, doc_ids, candidates, context) -> dict | None`

Requirements:

1. Pre-filter candidates by:
   - `collection_id`
   - `document_id in doc_ids`
   - normalized label match
2. If zero candidates:
   - return unresolved result with reason
3. If one candidate:
   - return selected candidate with trace
4. If multiple candidates:
   - call disambiguator and return winner + ranked alternatives

## 5.3 Disambiguation Rules (priority order)

Given multiple candidates, rank by:

1. Same document as source chunk
2. Closest section proximity
3. Latest timestamp
4. Highest confidence

Tie-breaker:

- Stable `chunk_id` / `target_id` ascending

---

## 6) Output Contract

Define models in `app/models/reference_resolution.py`:

- `ReferenceCandidate`
- `ResolvedReference`

Suggested fields:

- source identifiers (`source_chunk_id`, `source_document_id`, `collection_id`)
- reference payload (`reference_text`, `reference_type`, `target_label`)
- selected target (`target_chunk_id`, `target_document_id`, `target_section_label`)
- confidence and scoring details
- `match_trace` / `ranked_candidates`

---

## 7) Resolver Strategy for Phase 4

For this phase, resolver can operate on Phase 3 `filtered_chunks` as candidate space, provided scope guards are enforced.

Candidate generation from filtered chunks:

- all chunks in selected `(collection, doc_ids)` that carry compatible labels/sections/references
- optional references-derived candidates where available

This keeps Phase 4 deterministic and testable before deeper graph expansion in Phase 5.

---

## 8) Error and Edge-Case Policy

Expected behavior:

- missing collection -> explicit `ValueError`
- empty doc_ids -> empty resolver output
- malformed reference payload -> unresolved entry with reason, no crash
- unresolved reference -> include unresolved trace object

Never:

- resolve a target outside supplied `doc_ids`
- widen into other collections silently

---

## 9) Executor Integration

Update `traverse_references(filtered_chunks)` so it:

1. extracts all references from each source chunk
2. resolves each reference via scoped resolver/disambiguator
3. returns structured list of resolved/unresolved entries

`execute_plan` should surface this data in `references`.

---

## 10) Test Plan (Comprehensive)

## 10.1 Unit: `test_disambiguator.py`

Cover:

1. Same-document candidate outranks others.
2. Section proximity outranks distant section.
3. Latest timestamp outranks older when previous factors tie.
4. Confidence used as next tie-breaker.
5. Stable ordering on full tie.

## 10.2 Unit: `test_reference_resolver.py`

Cover:

1. Label normalization from `Table 3` and explicit `target_label`.
2. Scope filtering by collection/doc_ids.
3. Single-candidate direct resolution.
4. Multi-candidate disambiguation path.
5. Unresolved path emits reason metadata.

## 10.3 Integration: `test_reference_resolution_pipeline.py`

Scenarios:

1. Filtered chunks with overlapping labels across docs.
2. Resolver picks same-document candidate first.
3. Cross-collection negative case proves no leakage.
4. Executor returns resolved and unresolved entries with traces.

---

## 11) Cursor Agent Execution Packets

### Packet A - Disambiguator

```text
Task: Implement deterministic disambiguation scoring
Files: app/structure/disambiguator.py, tests/unit/test_disambiguator.py
Must preserve:
- ordered rules: same doc -> proximity -> latest timestamp -> confidence
- stable deterministic tie-break
Done when:
- disambiguator unit tests pass
```

### Packet B - Resolver

```text
Task: Implement scoped reference resolver + trace output
Files: app/structure/resolver.py, app/models/reference_resolution.py, tests/unit/test_reference_resolver.py
Must preserve:
- collection/doc scope gates
- normalized label matching
- unresolved reason metadata
Done when:
- resolver unit tests pass
```

### Packet C - Executor + Integration

```text
Task: Wire resolver into executor traversal and add integration coverage
Files: app/agent/executor.py, tests/integration/test_reference_resolution_pipeline.py
Must preserve:
- no scope widening
- structured resolved/unresolved outputs
Done when:
- integration tests pass
```

---

## 12) Implementation Checklist

- [ ] Disambiguator implemented with deterministic rule order
- [ ] Resolver enforces collection/doc scope + label normalization
- [ ] Resolver trace metadata includes rank rationale
- [ ] Executor traversal integrated with reference resolver
- [ ] Unit + integration tests cover positive and negative cases

---

## 13) Phase 4 Definition of Done

Phase 4 is complete only when:

1. References are resolved only within scoped `(collection, doc_ids)`.
2. Ambiguous references are disambiguated deterministically by documented rule order.
3. Resolver outputs include auditable trace metadata.
4. Unresolved references are explicitly represented with reasons.
5. Cross-collection/document leakage is prevented and test-validated.
