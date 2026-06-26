# Phase 7 Comprehensive Implementation Guide

## RAQE Phase 7 - API Integration + Error Handling

This document is the execution guide for Phase 7 implementation. It is designed for:

- Human developers
- Cursor agents executing scoped implementation packets

---

## 1) Phase 7 Objective

Expose the full RAQE pipeline behind stable FastAPI endpoints with typed request/response contracts and deterministic error handling.

Phase 7 must guarantee:

1. Thin route handlers delegate logic to query engine services.
2. Typed request/response schemas are enforced.
3. Known failure modes return structured, predictable errors.
4. API behavior remains collection/document scope-safe.

---

## 2) Inputs and Dependencies

Phase 7 depends on:

- Phase 1-6 pipeline implementation
- `QueryResult` contract from Phase 6
- Existing FastAPI app bootstrap

Primary references:

- `docs/reference_query_engine_final.md`
- `docs/raqe_phasewise_implementation_plan.md`
- `docs/phase6_implementation_comprehensive.md`

---

## 3) Scope Boundaries

Included:

- Route extraction into dedicated API module
- Request model (`question`, optional collection hints)
- Response model alignment (`QueryResult`)
- Error taxonomy and HTTP status mapping
- Integration tests for success/failure response contracts

Not included:

- Auth/rate-limiting middleware
- Deployment concerns

---

## 4) Target File Plan

Create/update these files:

- `app/models/query_request.py` (create)
- `app/api/query_routes.py` (create)
- `app/api/errors.py` (create)
- `app/agent/parser.py` (update for collection override + explicit missing collection)
- `app/agent/query_engine.py` (support route-level options)
- `app/main.py` (wire router)
- `tests/integration/test_phase7_api_contract.py` (create)

---

## 5) API Contract

## 5.1 Endpoint

- `POST /query/ask`

## 5.2 Request

Suggested payload:

```json
{
  "question": "Why did revenue change in Q1 FY24 for RELIANCE?",
  "collection": "RELIANCE",
  "section_hint": "4.2"
}
```

Rules:

- `question` required, non-empty after trim
- `collection` optional if resolvable from question text

## 5.3 Response

Return `QueryResult` shape (from Phase 6):

- `parsed_query`
- `plan`
- `execution`
- `context`
- `answer`

---

## 6) Error Taxonomy

Required error classes:

1. `invalid_query` -> HTTP 422
2. `missing_collection` -> HTTP 400
3. `no_documents_in_time_range` -> HTTP 404
4. `unresolved_reference` -> HTTP 422 (for strict-mode resolution failures)
5. `internal_error` -> HTTP 500 (guarded fallback)

Error payload shape:

```json
{
  "error": {
    "code": "missing_collection",
    "message": "Collection is required or must be resolvable from query."
  }
}
```

---

## 7) Service/Route Integration Rules

- Keep route thin: validate request, call `run_query`, map known failures.
- Do not embed parser/planner logic in route handlers.
- Preserve deterministic error messages for clients/tests.

---

## 8) Test Plan (Comprehensive)

## 8.1 Integration API tests

1. Success path returns full `QueryResult`.
2. Empty/blank question returns `invalid_query`.
3. Missing collection and not inferable returns `missing_collection`.
4. Valid query with no resolved documents returns `no_documents_in_time_range`.
5. Valid query with unresolved references returns `unresolved_reference`.

Use FastAPI `TestClient` and monkeypatch query engine where needed for deterministic tests.

---

## 9) Cursor Agent Execution Packets

### Packet A - Request/Error Models + Router

```text
Task: Add typed request/error models and route module
Files: app/models/query_request.py, app/api/errors.py, app/api/query_routes.py
Must preserve:
- stable error payload shape
- thin route handler
Done when:
- API integration tests pass for error taxonomy
```

### Packet B - Query Engine/Parser API Support

```text
Task: Add route-level collection/section overrides and missing-collection handling
Files: app/agent/parser.py, app/agent/query_engine.py
Must preserve:
- collection scope safety
- backward compatibility for existing run_query callers
Done when:
- existing tests remain green
```

### Packet C - App Wiring

```text
Task: Register router in FastAPI app bootstrap
Files: app/main.py
Must preserve:
- /health endpoint behavior
- /query/ask contract and status codes
Done when:
- full suite passes
```

---

## 10) Phase 7 Definition of Done

Phase 7 is complete only when:

1. API endpoint is backed by full RAQE pipeline.
2. Request and response contracts are typed and stable.
3. Error taxonomy is implemented with deterministic status codes/messages.
4. Integration tests validate all key success/failure behaviors.
