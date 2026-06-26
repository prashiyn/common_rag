# Phase 5 Comprehensive Implementation Guide

## RAQE Phase 5 - Graph Traversal + Multi-Hop Execution

This document is the execution guide for Phase 5 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 5 Objective

Implement bounded, collection-scoped graph traversal that expands resolved references across 1..2 hops and returns stable, deduplicated intermediate outputs for downstream context generation.

Phase 5 must guarantee:

1. All traversal starts from scoped `(collection_id, doc_ids)`.
2. Multi-hop expansion is bounded (`REFERS_TO*1..2`).
3. Executor outputs are deterministic and deduplicated.
4. Empty/null traversal paths are handled safely.

---

## 2) Inputs and Dependencies

Phase 5 depends on:

- Phase 2: document resolution (`doc_ids`)
- Phase 3: filtered chunks
- Phase 4: resolved references with trace metadata

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/raqe_phase_to_file_mapping.md`
- `docs/phase4_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Multi-hop cypher query templates for scoped traversal
- Graph traversal service wrapper
- Planner step alignment with execution flow
- Executor integration for events/reference traversal/table extraction
- Deterministic deduplication + null-safe handling
- Unit + integration tests

Not included:

- Final context rendering (Phase 6)
- API contract expansion (Phase 7)

---

## 4) Target File Plan

Create/update these files:

- `app/graph/queries.py` (add traversal queries)
- `app/graph/traversal.py` (create traversal service)
- `app/models/execution.py` (create typed intermediate outputs)
- `app/agent/planner.py` (update step mapping)
- `app/agent/executor.py` (wire traversal service + dedup)
- `tests/unit/test_planner_phase5.py` (create)
- `tests/unit/test_graph_traversal.py` (create)
- `tests/unit/test_executor_phase5.py` (create)
- `tests/integration/test_phase5_graph_execution.py` (create)

---

## 5) Functional Requirements

## 5.1 Planner Step Mapping

Planner must represent this sequence:

1. resolve documents
2. load/filter chunks
3. fetch events
4. traverse references (graph multi-hop)
5. fetch tables
6. build context
7. generate answer

## 5.2 Graph Traversal Service

Implement service API:

`traverse_reference_graph(collection, doc_ids, chunk_ids, max_hops=2, driver=None) -> list[dict]`

Requirements:

- enforce collection/doc scope
- return deterministic rows
- tolerate unavailable graph backend (return empty list, not crash)
- avoid widening scope on failures

## 5.3 Executor Intermediate Outputs

Implement typed intermediate structures for:

- `events`
- `reference_paths`
- `tables`

Ensure deduplication by stable keys.

---

## 6) Query Contract (Neo4j)

Add scoped traversal query:

- collection root match
- document filter `d.id IN $doc_ids`
- chunk filter `ch.id IN $chunk_ids`
- optional multi-hop expansion `REFERS_TO*1..2`

Result ordering must be deterministic by source/target identifiers.

---

## 7) Null/Empty Handling Policy

Required behavior:

- empty `doc_ids` or `chunk_ids` -> no graph call, return empty traversal
- null records from graph -> skip safely
- duplicate paths -> collapse to one canonical record

Never:

- raise due to missing optional fields
- return traversal rows from outside provided scope

---

## 8) Test Plan (Comprehensive)

## 8.1 Unit: planner

- verify planner contains required Phase 5 sequence

## 8.2 Unit: graph traversal service

- scoped call with parameters
- empty-input short-circuit
- dedup behavior
- backend failure returns empty list

## 8.3 Unit: executor

- events extraction from chunks is deterministic
- graph traversal wiring is used
- table extraction from resolved references is deduplicated

## 8.4 Integration: phase5 execution

- run `execute_plan` with mocked traversal rows
- assert output includes deduplicated `events/references/tables`
- assert no cross-collection/doc leakage in returned records

---

## 9) Cursor Agent Execution Packets

### Packet A - Queries + Traversal Service

```text
Task: Implement scoped multi-hop graph traversal service
Files: app/graph/queries.py, app/graph/traversal.py
Must preserve:
- collection/doc/chunk scoping
- no crash on backend unavailability
Done when:
- traversal unit tests pass
```

### Packet B - Planner + Executor

```text
Task: Align planner/executor with Phase 5 step mapping and typed intermediates
Files: app/agent/planner.py, app/agent/executor.py, app/models/execution.py
Must preserve:
- deterministic deduplication
- null-safe behavior
Done when:
- planner/executor unit tests pass
```

### Packet C - Integration Tests

```text
Task: Validate end-to-end Phase 5 execution path
Files: tests/integration/test_phase5_graph_execution.py
Must preserve:
- bounded scope behavior
- deterministic output set
Done when:
- integration tests pass
```

---

## 10) Phase 5 Definition of Done

Phase 5 is complete only when:

1. Multi-hop graph traversal is collection/document scoped.
2. Planner and executor sequence match the intended flow.
3. `events`, `references`, and `tables` are deterministic and deduplicated.
4. Null/empty graph responses are handled without failures.
5. Tests confirm no scope leakage and stable behavior.
