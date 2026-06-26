# Phase 6 Comprehensive Implementation Guide

## RAQE Phase 6 - Context Builder + Answer Contract

This document is the execution guide for Phase 6 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 6 Objective

Implement a structured, provenance-rich context layer and a stable answer contract that can be consumed by downstream API and client layers.

Phase 6 must guarantee:

1. Context includes collection/document/chunk provenance.
2. Fiscal period and section context are carried forward.
3. References and tables are represented in auditable evidence blocks.
4. Answer payloads follow a deterministic schema.

---

## 2) Inputs and Dependencies

Phase 6 depends on:

- Phase 2: document resolution metadata
- Phase 3: filtered chunks
- Phase 4: reference resolution traces
- Phase 5: deduplicated intermediate execution outputs

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`
- `docs/phase5_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Context contract model and builder
- Answer contract model and generator
- Query engine output wiring to typed response
- Unit + integration tests for context/answer payloads

Not included:

- HTTP API contract routing changes (Phase 7)
- LLM provider integration improvements

---

## 4) Target File Plan

Create/update these files:

- `app/models/query_response.py` (create)
- `app/agent/context_builder.py` (replace placeholder)
- `app/agent/answer_generator.py` (replace placeholder)
- `app/agent/query_engine.py` (wire contract)
- `tests/unit/test_context_builder.py` (create)
- `tests/unit/test_answer_generator.py` (create)
- `tests/integration/test_phase6_query_contract.py` (create)

---

## 5) Functional Requirements

## 5.1 Context Builder

`build_context(data: dict) -> dict`

Must include:

- `summary`:
  - counts for documents/chunks/events/references/tables
- `documents`:
  - `document_id`
  - `collection_id`
  - fiscal metadata when available
- `evidence` list with chunk-level provenance:
  - `collection_id`, `document_id`, `chunk_id`, `timestamp`
  - section metadata
  - content snippet/title summary
- `reference_traces`:
  - resolved/unresolved outcomes and reasons
- `table_evidence`:
  - table-targeted items for numeric support

## 5.2 Answer Generator

`generate_answer(question: str, context: dict) -> dict`

Must return deterministic contract:

- `question`
- `direct_answer` (concise placeholder synthesis from context counts for now)
- `confidence` (bounded numeric heuristic)
- `supporting_facts` (small list from evidence/references)
- `context_summary`

No free-form string-only output.

## 5.3 Query Engine Contract

`run_query` should return:

- `parsed_query`
- `plan`
- `execution` (raw execution payload)
- `context` (structured context object)
- `answer` (structured answer object)

---

## 6) Data Contract (Recommended)

Use models in `app/models/query_response.py`:

- `ContextSummary`
- `ContextEvidenceItem`
- `ReferenceTraceItem`
- `TableEvidenceItem`
- `QueryContext`
- `QueryAnswer`
- `QueryResult`

All fields should be JSON-serializable and deterministic.

---

## 7) Determinism and Safety Rules

- Never drop provenance identifiers when constructing evidence.
- Always include unresolved reference reasons.
- Keep output ordering stable:
  - documents by `document_id`
  - evidence by `timestamp` desc then `chunk_id`
- Handle missing optional fields safely with defaults.

---

## 8) Test Plan (Comprehensive)

## 8.1 Unit: context builder

- includes required summary counts
- includes provenance fields in evidence
- preserves unresolved references
- deterministic ordering

## 8.2 Unit: answer generator

- returns required keys and bounded confidence
- creates supporting facts from context
- behaves safely with sparse/empty context

## 8.3 Integration: query contract

- `run_query` returns full contract object
- `context` and `answer` have expected structure
- contract remains stable with mocked execution data

---

## 9) Cursor Agent Execution Packets

### Packet A - Context Models + Builder

```text
Task: Implement typed context contract and builder
Files: app/models/query_response.py, app/agent/context_builder.py
Must preserve:
- provenance completeness
- stable ordering
Done when:
- context builder unit tests pass
```

### Packet B - Answer Contract

```text
Task: Implement structured answer generator
Files: app/agent/answer_generator.py, app/models/query_response.py
Must preserve:
- deterministic schema
- confidence bounds
Done when:
- answer generator unit tests pass
```

### Packet C - Query Engine Integration

```text
Task: Wire context/answer contracts into run_query and validate integration
Files: app/agent/query_engine.py, tests/integration/test_phase6_query_contract.py
Must preserve:
- full query contract fields
- backward-safe execution passthrough
Done when:
- integration tests pass
```

---

## 10) Phase 6 Definition of Done

Phase 6 is complete only when:

1. Context includes auditable provenance and required metadata.
2. Answer payload follows stable structured contract.
3. Query engine returns structured `execution/context/answer` payloads.
4. Unit and integration tests verify completeness and determinism.
