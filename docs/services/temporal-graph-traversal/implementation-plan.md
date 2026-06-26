# RAQE Phase-Wise Implementation Plan (Human + Cursor Agent Ready)

## 1) Purpose

This document translates the product specification into an execution plan for building a production-ready **Reference-Aware Query Engine (RAQE)** as a **FastAPI server** with:

- Chunk-level ingestion and retrieval (not document blobs)
- Collection-scoped documents that each contain chunk lists
- Collection/document/time-scoped graph reasoning
- Reference resolution + disambiguation
- Multi-hop traversal and context assembly for answers

This plan is designed for:

- Humans: clear sequencing, ownership, acceptance criteria
- Cursor agents: actionable task slices with concrete completion checks

---

## 2) Ground Truth Requirements (From Final Spec)

The implementation must preserve these invariants:

0. **Canonical schema invariant**: `ChunkItem` in `docs/doc_processing_openapi.json` is the golden input contract.
1. **Chunk-first architecture**: all pipeline logic runs on `chunk_id` units.
2. **Hierarchy invariant**: `Collection -> Document -> [Chunks]` is mandatory for ingestion and retrieval.
3. **Scope triad for correctness**: `(collection_id + document_id + label)` for reference resolution.
4. **Temporal reasoning**: queries resolve document scope using explicit or inferred time context.
5. **Graph-first traversal**: collection/document filtering before reference expansion.
6. **Disambiguation rules (priority order)**:
   - Same document > others
   - Closest section > distant
   - Latest timestamp > older
   - Highest confidence
7. **Context payload must include**: `collection_id`, `document_id`, `chunk_id`, fiscal period, section context.

### Canonical-to-RAQE Mapping Requirement

Phase implementation must explicitly map canonical fields from `ChunkItem` to RAQE fields:

- `doc_id` -> `document_id`
- `section_title` -> normalized section identity (`section_id`/`section_label`, when derivable)
- `publish_date` -> normalized temporal fields (`timestamp`, `period`, `fiscal_year`, via resolver/enrichment)
- `references[]` -> graph reference edges + resolver candidates

Do not redefine or drift from the OpenAPI chunk contract.

---

## 3) Target Architecture

## Runtime

- FastAPI server (`app/main.py`)
- Orchestrated query engine (`app/agent/query_engine.py`)
- `uv` for package/project management
- Centralized runtime config in `app/config.py`
- `.env.example` lists every required environment variable

## Core Modules

- `app/agent/parser.py`
- `app/agent/planner.py`
- `app/agent/executor.py`
- `app/agent/context_builder.py`
- `app/agent/answer_generator.py`
- `app/graph/neo4j_client.py`
- `app/graph/queries.py`
- `app/structure/resolver.py`

---

## 4) Phase Plan

Each phase includes: objective, implementation tasks, outputs, and done criteria.

### Phase 0 - Project Foundations

**Objective:** Establish baseline server + conventions.

**Tasks**

1. Initialize/update `pyproject.toml` with required dependencies (`fastapi`, `uvicorn`, `neo4j`, `pydantic-settings`).
2. Confirm project runs with `uv` (`uv sync`, `uv run uvicorn ...`).
3. Ensure `app/config.py` is single source for runtime settings.
4. Ensure `.env.example` includes app + Neo4j variables.
5. Add basic health endpoint.

**Outputs**

- Running FastAPI app
- Config and env template aligned

**Done Criteria**

- `GET /health` returns success payload
- App runs with only `.env` (derived from `.env.example`)

---

### Phase 1 - Graph Data Model + Ingestion Contract

**Objective:** Lock graph schema and chunk ingestion payload contract.

**Tasks**

1. Define/validate chunk schema fields:
   - canonical `ChunkItem` fields from OpenAPI schema
2. Define and validate RAQE normalized/enriched fields:
   - `collection_id`, `section_id`, `section_label`, normalized `timestamp`, `period`, `fiscal_year`
3. Define/validate document payload schema that contains `chunks: list[ChunkItem]`.
4. Implement ingestion contract validators (Pydantic models).
5. Implement canonical-to-RAQE mapping/enrichment layer.
6. Ensure ingestion path materializes `Collection -> Document -> Chunk` lineage.
7. Ensure graph nodes carry required identifiers:
   - `collection_id` across relevant nodes
   - `document_id` across `Section`/`Table`
8. Ensure references extracted from chunks are persisted in graph relations.

**Outputs**

- Typed ingestion models
- Canonical-to-RAQE field mapping spec + implementation
- Schema migration/init scripts (if needed)
- Ingestion tests with sample payload

**Done Criteria**

- Sample chunk ingest creates/links `Collection -> Document -> Section -> Table`
- Sample document ingest preserves `Document -> [Chunks]` mapping end-to-end
- Canonical `ChunkItem` payloads are accepted without schema drift
- Reference metadata survives ingestion

---

### Phase 2 - Temporal Resolver + Document Scope Resolution

**Objective:** Convert user time expressions into scoped `doc_ids`.

**Tasks**

1. Implement `parse_time()` in parser pipeline (explicit dates, quarter/year phrases, relative windows like "last quarter").
2. Implement `resolve_documents(collection, time_context)`:
   - Always filter by collection first
   - Then filter/select documents by timestamp/period/fiscal year
3. Add fallback behavior for ambiguous time:
   - default to latest document set
   - expose selected time scope in metadata

**Outputs**

- Time context model
- Document resolver service
- Resolver unit tests for representative queries

**Done Criteria**

- Given collection + time phrase, resolver returns deterministic ordered doc IDs
- Resolver behavior is documented and test-covered

---

### Phase 3 - Chunk Filtering Layer

**Objective:** Build chunk retrieval constrained by resolved `doc_ids`.

**Tasks**

1. Implement `load_document_chunks(collection, doc_ids)` abstraction.
2. Implement `filter_chunks(collection, doc_ids)` on top of loaded document chunk lists.
3. Add optional section-based narrowing from parsed intent/target terms.
4. Return chunk payloads with enough metadata for downstream scoring/disambiguation.

**Outputs**

- Chunk filter service
- Query patterns for performant retrieval

**Done Criteria**

- No chunk outside selected documents enters execution path
- All processed chunks can be traced to exactly one resolved document in the selected collection
- Chunk filtering latency is within baseline target (define in perf sheet)

---

### Phase 4 - Reference Resolver (Scoped + Deterministic)

**Objective:** Resolve references like "Table 3" accurately across multi-doc collections.

**Tasks**

1. Implement `resolve_reference(ref, collection, doc_ids)` with scope gates:
   - `collection_id` filter
   - `document_id` filter
   - label match normalization (`Table 3` -> `3`)
2. Add ambiguity handling with explicit disambiguation scoring.
3. Persist/return resolver trace metadata (why this node was selected).

**Outputs**

- Reference resolver module
- Normalization utilities
- Resolver trace format

**Done Criteria**

- Ambiguous labels across documents resolve correctly under rule hierarchy
- Resolver can explain selected target with ranked candidates

---

### Phase 5 - Graph Traversal + Multi-Hop Execution

**Objective:** Execute scoped graph plan with reference expansion.

**Tasks**

1. Update cypher queries to enforce:
   - collection match
   - `d.id IN $doc_ids`
2. Traverse from sections to referenced nodes (`REFERS_TO*1..2` as needed).
3. Implement planner-to-executor step mapping for:
   - event extraction
   - reference traversal
   - table retrieval
4. Add robust null/empty path handling.

**Outputs**

- Production cypher query set
- Executor with typed intermediate outputs

**Done Criteria**

- Execution path never leaks outside selected collection/doc scope
- Multi-hop traversal returns stable, deduplicated results

---

### Phase 6 - Context Builder + Answer Contract

**Objective:** Build answer-ready, provenance-rich context blocks.

**Tasks**

1. Implement structured context format including:
   - `document_id`
   - fiscal period metadata
   - section snippets
   - resolved reference details
2. Include provenance fields (`chunk_id`, section label, confidence, timestamp).
3. Define response schema from query endpoint.

**Outputs**

- Context builder implementation
- API response model with answer + evidence

**Done Criteria**

- Every answer includes auditable context and source metadata
- Context contains all required spec fields

---

### Phase 7 - API Integration + Error Handling

**Objective:** Expose complete RAQE flow behind stable FastAPI API.

**Tasks**

1. Wire route (`POST /query/ask`) to full pipeline:
   - parse -> time resolve -> document resolve -> load document chunks -> chunk filter -> execute -> context -> answer
2. Add error taxonomy:
   - invalid query
   - missing collection
   - no documents in time range
   - unresolved reference
3. Add request/response models and meaningful HTTP status codes.

**Outputs**

- Query API endpoint (production path)
- Standardized error responses

**Done Criteria**

- Endpoint handles success + known failure classes deterministically
- API contract documented for clients

---

### Phase 8 - Quality Gates (Tests, Observability, Performance)

**Objective:** Make engine reliable, inspectable, and regression-safe.

**Tasks**

1. Unit tests:
   - time parsing
   - document resolver
   - reference resolver/disambiguation
2. Integration tests:
   - end-to-end query on seeded test graph
3. Add structured logging at each major stage:
   - parsed query
   - selected docs/chunks
   - disambiguation outcome
4. Add baseline metrics:
   - query latency
   - traversal fanout
   - unresolved-reference rate

**Outputs**

- Test suite (unit + integration)
- Observability instrumentation

**Done Criteria**

- CI passes on deterministic test graph snapshots
- Key latency + correctness metrics are available

---

### Phase 9 - Backtesting + Signal Validation Layer

**Objective:** Implement the next-step roadmap item from spec.

**Tasks**

1. Define evaluation datasets and expected answers.
2. Implement replay harness for historical queries.
3. Compare output consistency across document vintages.
4. Score answer quality and reference correctness.

**Outputs**

- Backtesting runner
- Validation report format

**Done Criteria**

- Repeatable quality report generated for each run
- Regression thresholds defined and enforced

---

## 5) Cross-Phase Technical Standards

1. Use `uv` for dependency/project tasks.
2. Keep all runtime/env settings in `config.py`; no scattered config.
3. Every new env variable must be mirrored in `.env.example`.
4. Prefer typed models and explicit schemas over loose dicts at API boundaries.
5. Preserve modular boundaries (parser/planner/executor/context/answer).

---

## 6) Suggested Build Order for Cursor Agents

Use this sequence when delegating to agents:

1. Foundations + config alignment (Phase 0)
2. Schema + ingestion typing (Phase 1)
3. Temporal/document resolver (Phase 2)
4. Chunk filtering + scoped queries (Phase 3 + 5 partial)
5. Reference resolver + disambiguation (Phase 4)
6. Context + endpoint contract (Phase 6 + 7)
7. Tests + observability (Phase 8)
8. Backtesting layer (Phase 9)

---

## 7) Agent Task Template (Copy/Paste)

Use this template for each implementation task:

```text
Task: <phase + component name>
Goal: <single measurable outcome>
Inputs: <files/spec dependencies>
Constraints:
- Must preserve collection/document/time scope
- Must use config.py for settings
- Must keep .env.example updated for new env vars
- Must keep endpoint thin; logic in services
Deliverables:
- Code changes in listed files
- Tests for success + edge cases
- Short note on assumptions
Done when:
- <explicit acceptance checks>
```

---

## 8) Phase Exit Checklist

A phase is complete only if:

- Implementation matches phase done criteria
- Tests for new behavior exist and pass
- No scope leakage across collection/document boundaries
- Config/env updates are synchronized
- API/contract changes are documented

---

## 9) Definition of Overall Done (Project)

RAQE is production-ready when:

1. Query endpoint serves chunk-grounded, provenance-backed answers.
2. Every query preserves the `Collection -> Document -> Chunk` lineage through execution.
3. Temporal + document disambiguation is deterministic and test-validated.
4. Cross-reference traversal is accurate under collection/document scope.
5. End-to-end observability and regression tests are in place.
6. Backtesting framework reports stability across historical scenarios.
