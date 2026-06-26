# RAQE Phase-to-File Mapping (Collection-First Execution)

## 1) Core Constraint (Non-Negotiable)

The system must always reason in this order:

1. `collection_id` scope first
2. `document_id` scope second
3. load chunk list from scoped documents
4. chunk/section/reference operations only inside those scoped document chunks

If a step cannot prove collection + document scope, it is incomplete.

---

## 2) Global Implementation Rules

- Always model grouping as `Collection -> HAS_DOCUMENT -> Document`.
- Always model content ownership as `Document -> [Chunks]`.
- Treat `docs/doc_processing_openapi.json` `ChunkItem` as the canonical raw chunk contract.
- Never run chunk retrieval or reference traversal across full corpus by default.
- Every resolver and query function should accept scoped identifiers (`collection`, `doc_ids`).
- Keep time resolution tied to selected documents, not free-floating chunks.
- Keep FastAPI routes thin; all scope logic lives in services/modules.

---

## 3) Phase-by-Phase File Mapping

## Phase 0 - Foundations

**Goal:** Boot runtime and enforce project conventions.

**Files**

- `pyproject.toml`
- `.env.example`
- `app/config.py`
- `app/main.py`

**Implement**

- `uv`-managed dependencies and run path
- app + Neo4j settings in `config.py`
- basic health endpoint and request model scaffolding

**Collection Guardrail**

- Add comments/type hints indicating all query paths require collection scope.

---

## Phase 1 - Data Contracts + Ingestion Shape

**Goal:** Ensure chunk ingestion carries collection/document lineage.

**Files**

- `app/models/ingestion.py` (create)
- `app/models/graph_entities.py` (create)
- `app/ingestion/chunk_ingestor.py` (create)
- `app/ingestion/document_ingestor.py` (create)
- `app/graph/queries.py`

**Implement**

- Canonical models matching `ChunkItem` and `ChunkReferenceItem`
- mapping layer from canonical chunk payload to RAQE normalized fields
- document payload schema with `chunks: list[Chunk]`
- Pydantic chunk schema with required fields:
  - canonical fields (`chunk_id`, `content`, `type`, `doc_id`, `page`, `bundle_id`, `section_title`, `title_summary`, `publish_date`, `prev_chunk`, `next_chunk`, `references[]`)
- graph upsert contract for `Collection`, `Document`, `Section`, `Table`
- document-chunk linkage persistence (`Document -> Chunk`)
- chunk reference persistence logic

**Collection Guardrail**

- Reject ingestion payloads missing `collection_id` or `doc_id`.
- Reject document payloads with empty or invalid `chunks` lists.
- Reject/flag payloads that violate canonical `ChunkItem` requirements.

---

## Phase 2 - Temporal Parsing + Document Resolver

**Goal:** Resolve query time context into scoped document IDs under one collection.

**Files**

- `app/agent/parser.py`
- `app/agent/time_resolver.py` (create)
- `app/agent/document_resolver.py` (create)
- `app/graph/queries.py`

**Implement**

- `parse_time(question)` support for quarter/year/relative expressions
- `resolve_documents(collection, time_context)` returning ordered `doc_ids`
- deterministic fallback to latest doc set when time is absent/ambiguous

**Collection Guardrail**

- `resolve_documents` must require `collection`; no global resolution API.

---

## Phase 3 - Chunk Filtering Layer

**Goal:** Restrict retrieval to resolved documents before planning/execution.

**Files**

- `app/agent/executor.py`
- `app/agent/chunk_filter.py` (create)
- `app/agent/document_chunk_loader.py` (create)
- `app/graph/queries.py`

**Implement**

- `load_document_chunks(collection, doc_ids)` from document-owned chunk lists
- `filter_chunks(doc_ids, optional_targets)` with metadata-rich return payloads
- optional section narrowing from query intent

**Collection Guardrail**

- `filter_chunks` should only consume `doc_ids` previously resolved for the same collection.
- `filter_chunks` must operate only on chunks loaded from those scoped documents.

---

## Phase 4 - Reference Resolver + Disambiguation

**Goal:** Resolve references (e.g., Table 3) with strict scope and ranking.

**Files**

- `app/structure/resolver.py`
- `app/structure/disambiguator.py` (create)
- `app/graph/queries.py`

**Implement**

- `resolve_reference(ref, collection, doc_ids)`
- candidate ranking rules:
  1. same document
  2. closest section proximity
  3. latest timestamp
  4. highest confidence
- normalized label matching (`Table 3` -> `3`)

**Collection Guardrail**

- candidate set must be pre-filtered by `collection_id`, then `document_id`.

---

## Phase 5 - Graph Traversal + Planner/Executor Integration

**Goal:** Execute multi-hop graph traversal with bounded scope.

**Files**

- `app/agent/planner.py`
- `app/agent/executor.py`
- `app/graph/queries.py`
- `app/graph/neo4j_client.py`

**Implement**

- planner steps aligned to parse -> resolve docs -> filter chunks -> traverse refs -> build context
- planner steps aligned to parse -> resolve docs -> load document chunks -> filter chunks -> traverse refs -> build context
- cypher templates using:
  - collection match
  - `WHERE d.id IN $doc_ids`
  - optional reference expansion (`REFERS_TO*1..2`)
- deduplication of traversal outputs

**Collection Guardrail**

- all cypher entry points start from collection node and scoped documents.

---

## Phase 6 - Context Builder + Answer Contract

**Goal:** Produce evidence-rich response payloads.

**Files**

- `app/agent/context_builder.py`
- `app/agent/answer_generator.py`
- `app/models/query_response.py` (create)

**Implement**

- context blocks including:
  - `document_id`
  - fiscal period
  - section context
  - reference trace
  - `chunk_id` provenance
- stable response schema for API clients

**Collection Guardrail**

- each context item includes both `collection_id` and `document_id`.

---

## Phase 7 - API Endpoint Completion

**Goal:** Wire full RAQE flow behind FastAPI route.

**Files**

- `app/main.py`
- `app/api/query_routes.py` (create)
- `app/models/query_request.py` (create)
- `app/models/query_response.py`

**Implement**

- `POST /query/ask` with typed models
- service orchestration call to `run_query`
- structured errors for missing collection/no docs/unresolved refs

**Collection Guardrail**

- request contract must include collection or resolvable collection alias.

---

## Phase 8 - Tests + Observability

**Goal:** Lock correctness and diagnose scope leaks.

**Files**

- `tests/unit/test_time_resolver.py` (create)
- `tests/unit/test_document_resolver.py` (create)
- `tests/unit/test_reference_resolver.py` (create)
- `tests/integration/test_query_pipeline.py` (create)
- `app/observability/logging.py` (create)

**Implement**

- unit tests for temporal and disambiguation logic
- integration tests on seeded graph data
- stage-level logs: selected collection/docs/chunks/candidate refs

**Collection Guardrail**

- add negative tests asserting no cross-collection leakage.

---

## Phase 9 - Backtesting + Signal Validation

**Goal:** Evaluate stability over historical scenarios.

**Files**

- `app/backtesting/replay_runner.py` (create)
- `app/backtesting/metrics.py` (create)
- `tests/backtesting/test_replay_regressions.py` (create)
- `docs/backtesting_protocol.md` (create)

**Implement**

- replay historical queries against document vintages
- evaluate answer consistency + reference correctness
- generate regression summary artifacts

**Collection Guardrail**

- reports must include per-collection metrics and leakage checks.

---

## 4) Required Function Signatures (Recommended)

Use/align these signatures to keep orchestration consistent:

```python
def parse_query(question: str) -> dict: ...
def parse_time(question: str) -> dict: ...
def map_chunkitem_to_raqe(chunk: dict, collection_id: str) -> dict: ...
def resolve_documents(collection: str, time_context: dict) -> list[str]: ...
def load_document_chunks(collection: str, doc_ids: list[str]) -> dict[str, list[dict]]: ...
def filter_chunks(collection: str, doc_ids: list[str], target: str | None = None) -> list[dict]: ...
def resolve_reference(ref: dict, collection: str, doc_ids: list[str]) -> dict | None: ...
def disambiguate(candidates: list[dict], context: dict) -> dict | None: ...
def execute_plan(plan: dict, query: dict) -> dict: ...
def build_context(result: dict) -> dict: ...
def generate_answer(question: str, context: dict) -> dict: ...
```

---

## 5) Cursor Agent Work Packet Strategy

Create one agent task per phase using this compact packet:

```text
Phase: <N>
Files: <exact paths listed above>
Implement: <3-7 bullet tasks from phase section>
Must preserve:
- collection-first scoping
- document scoping before chunk/ref traversal
- chunk operations only on chunks owned by resolved documents
- config.py + .env.example sync for new settings
Acceptance:
- run tests for touched modules
- include one negative test for scope leakage (where applicable)
```

---

## 6) Review Checklist for Every PR

- Does this change start from collection scope?
- Are document IDs resolved before chunk/reference operations?
- Are chunks loaded from the resolved documents (not global chunk scans)?
- Could this query accidentally touch other collections?
- Are disambiguation decisions traceable and test-covered?
- Are config/env updates complete and synchronized?
