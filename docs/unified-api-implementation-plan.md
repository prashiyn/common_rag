# Unified API Implementation Plan

**Objective:** Merge the seven independent FastAPI microservices into a single FastAPI process served from a new `unified_api/` directory at the repository root. All external API contracts (URL paths, request/response schemas) are preserved. Each service retains its own database connections and schemas. `fin_rag` is out of scope and stays as a separate service.

**Status:** `PENDING` — no code has been written yet.

**Document version:** 1.1 — June 2026

---

## Table of Contents

1. [Background and Motivation](#1-background-and-motivation)
2. [Architecture Overview](#2-architecture-overview)
3. [Service Inventory](#3-service-inventory)
4. [Route Prefix Map](#4-route-prefix-map)
5. [Dependency Analysis](#5-dependency-analysis)
6. [Pre-conditions and Setup](#6-pre-conditions-and-setup)
7. [Step 1 — Enable packaging for `temporial_graph_traversal`](#step-1--enable-packaging-for-temporial_graph_traversal)
8. [Step 2 — Refactor inline routes to `APIRouter` (three services)](#step-2--refactor-inline-routes-to-apirouter-three-services)
9. [Step 3 — Create `unified_api/` skeleton](#step-3--create-unified_api-skeleton)
10. [Step 4 — Create `unified_api/pyproject.toml`](#step-4--create-unified_apipyprojecttoml)
11. [Step 5 — Create unified settings module](#step-5--create-unified-settings-module)
12. [Step 6 — Create unified lifespan](#step-6--create-unified-lifespan)
13. [Step 7 — Wire all routers into `unified_api/main.py`](#step-7--wire-all-routers-into-unified_apimainpy)
14. [Step 8 — Create `unified_api/Dockerfile.compose`](#step-8--create-unified_apidockerfilecompose)
15. [Step 9 — Update `docker-compose.yml`](#step-9--update-docker-composeyml)
16. [Step 10 — Update `docker-compose-test.yaml`](#step-10--update-docker-compose-testyaml)
17. [Step 11 — Merge environment variable files](#step-11--merge-environment-variable-files)
18. [Step 12 — Validation checklist](#step-12--validation-checklist)
19. [Step 13 — Unify documentation into `docs/`](#step-13--unify-documentation-into-docs)
20. [Phase 2 — Optimise internal LLM calls (optional)](#phase-2--optimise-internal-llm-calls-optional)
21. [What does NOT change](#what-does-not-change)
22. [Complete file change summary](#complete-file-change-summary)
23. [Rollback procedure](#rollback-procedure)

---

## 1. Background and Motivation

The repository currently runs **seven independent FastAPI services**, each with its own Docker container, port, build, and `.env` file:

| Service | Container port | Host port |
|---------|---------------|-----------|
| `llm-service` | 8001 | 8020 |
| `doc_processing` | 8000 | 8010 |
| `core_rag_graph` | 20050 | 20050 |
| `ra_literag` | 8000 | 8000 |
| `temporial_graph` | 8082 | 8082 |
| `temporial_graph_openai` | 8080 | 8080 |
| `temporial_graph_traversal` | 8090 | 8090 |

**Problems with this setup:**
- Seven separate builds, seven Docker images, seven `.env` files.
- Every service calls `llm-service` over HTTP; adds latency and complexity.
- Starting the full stack requires `depends_on` chains across seven services.
- Updating a shared dependency (e.g. `pydantic`) requires editing seven `pyproject.toml` files.

**Goal:** One Docker image, one process, one port (`8000`), one `.env`, one build. All APIs remain callable at the same contract (schemas unchanged). Each service keeps its own database and schema.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  unified_api  (port 8000)                    │
│                                                              │
│  GET /health                   ← unified liveness probe      │
│                                                              │
│  /llm-service/*                ← llm_service routers         │
│  /doc-processing/*             ← doc_processing routers      │
│  /core-rag/*                   ← core_rag_graph routers      │
│  /ra-literag/*                 ← ra_literag routers          │
│  /temporal-graph/*             ← temporial_graph routers     │
│  /temporal-graph-openai/*      ← temporial_graph_openai      │
│  /temporal-graph-traversal/*   ← temporial_graph_traversal   │
└───────────────────────┬─────────────────────────────────────┘
                        │ single process, single event loop
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
     postgres        neo4j          chroma
      (5432)         (7687)         (8000)
                        │
                     ollama
                    (11434)
```

**Key design decisions:**

| Decision | Choice | Reason |
|----------|--------|--------|
| Route prefixes | Added per service (e.g. `/llm-service/`) | Five services share conflicting paths like `/health`, `/v1/`, `/collections` |
| Request/response schemas | **Unchanged** | User requirement; external consumers must not break |
| Database schemas | **Unchanged** | Each service keeps its own tables/labels/collections |
| Python version | **3.12** | `temporial_graph_openai` requires `>=3.12`; all others support ≥3.10/3.11 |
| Service Settings classes | **Each service keeps its own** | Avoids a god-object; `NEO4J_URI` is read independently by each service that needs it |
| Inter-service HTTP calls | HTTP to `http://localhost:8000` in Phase 1 | Safe; can be optimised to direct imports in Phase 2 |
| Unified app location | `unified_api/` at repo root | Per-service code is untouched; clean separation |
| `fin_rag` | **Out of scope** | Not in the original seven; stays as a separate service |

---

## 3. Service Inventory

### 3.1 `llm-service`

- **Main file:** `llm-service/src/llm_service/main.py`
- **Package name:** `llm-service` (`src/llm_service/`)
- **Routers (already use `APIRouter`):**
  - `llm_service/routers/health.py` → prefix `/health`
  - `llm_service/routers/llm.py` → prefix `/llm`
  - `llm_service/routers/openai.py` → prefix `/v1`
- **Lifespan:** empty `yield`; all config applied in `create_app()` before FastAPI init
- **External systems:** Ollama (via LiteLLM), Groq/OpenAI/Anthropic API keys (via LiteLLM)
- **Key env vars:** `OLLAMA_API_BASE`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_PLAN`, `CONFIG_DIR`
- **Needs router refactor:** No ✓

### 3.2 `doc_processing`

- **Main file:** `doc_processing/src/doc_processing/main.py`
- **Package name:** `doc-processing` (`src/doc_processing/`)
- **Routers (already use `APIRouter`):**
  - `doc_processing/routers/health.py` → prefix `/health`
  - `doc_processing/routers/documents.py` → prefix `/documents`
- **Lifespan:** calls `configure_debug_logging()` then `yield`
- **External systems:** Ollama (direct HTTP for Docling VLM), `llm-service` (HTTP)
- **Key env vars:** `OLLAMA_BASE_URL`, `LLM_SERVICE_BASE_URL`, `DOC_PROCESSING_TEMP_DIR`
- **Needs router refactor:** No ✓

### 3.3 `core_rag_graph`

- **Main file:** `core_rag_graph/graph_server.py`
- **Package name:** `core-rag-graph` (flat layout, no `src/`)
- **Routers:** **None** — all 30+ routes are `@app.get/post/delete` on the `app` object directly
- **Lifespan:** uses deprecated `@app.on_event("shutdown")` → calls `GRAPH_REPOSITORY.close()`
- **External systems:** Neo4j (when `GRAPH_BACKEND=neo4j`), NetworkX JSON files, `llm-service` (HTTP)
- **Key env vars:** `GRAPH_BACKEND`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `LLM_SERVICE_BASE_URL`
- **Needs router refactor:** **Yes — Step 2a**

### 3.4 `ra_literag`

- **Main file:** `ra_literag/app/main.py`
- **Package name:** `ra-literag` (`app/` + `raganything/` at repo root)
- **Routers:** **None** — all routes are inline `@app.get/post` with tag annotations
- **Lifespan:** startup → `db_config.init_pool()`, preload workspace RAG instances; shutdown → `rag.finalize_storages()`, `db_config.close_pool()`
- **External systems:** Neo4j (LightRAG graph store), Chroma (LightRAG vectors), PostgreSQL (workspace config table), `llm-service` (HTTP)
- **Key env vars:** `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `CHROMA_HOST`, `CHROMA_PORT`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE`, `LLM_SERVICE_BASE_URL`
- **Needs router refactor:** **Yes — Step 2b**

### 3.5 `temporial_graph`

- **Main file:** `temporial_graph/src/temporial_graph_rag/api/main.py`
- **Package name:** `temporial-graph-rag` (`src/temporial_graph_rag/`)
- **Routers:** **None** — all routes inline with `@app.get/post`
- **Lifespan:** startup → `load_dotenv`, init `Neo4jGraphStore` or in-memory `CollectionRegistry`, optional LLM probe; shutdown → `store.close()`
- **External systems:** Neo4j, `llm-service` (HTTP)
- **Key env vars:** `NEO4J_ENABLED`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `LLM_SERVICE_BASE_URL`, `LLM_STARTUP_MODELS_CHECK`
- **Needs router refactor:** **Yes — Step 2c**

### 3.6 `temporial_graph_openai`

- **Main file:** `temporial_graph_openai/temporal_graph/api/main.py`
- **Package name:** `temporal-graph-openai` (`temporal_graph/`)
- **Routers (already use `APIRouter`):**
  - `temporal_graph/api/ingest_routes.py` → prefix `/v1`, tag `ingest`
  - `temporal_graph/api/retrieve_routes.py` → prefix `/v1`, tag `retrieve`
  - `temporal_graph/api/collection_routes.py` → prefix `/v1`, tag `collections`
  - Root `GET /health` is inline on `app`
- **Lifespan:** startup → `JobManager`, optional Redis ingest worker, `bootstrap_graph()` (Neo4j schema); shutdown → stop worker, close job manager, close Neo4j driver
- **External systems:** Neo4j (async driver), `llm-service` (HTTP), Redis (optional job backend)
- **Key env vars:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `LLM_SERVICE_BASE_URL`, `JOB_BACKEND`, `REDIS_URL`
- **Needs router refactor:** Partial — `/health` needs extraction (Step 2d)

### 3.7 `temporial_graph_traversal`

- **Main file:** `temporial_graph_traversal/app/main.py`
- **Package name:** `reference-aware-query-engine` (`app/` at repo root, **`uv.package = false`**)
- **Routers (already use `APIRouter`):**
  - `app/api/query_routes.py` → prefix `/query`, tag `query`
  - `app/api/collection_routes.py` → prefix `/collections`, tag `collections`
  - Root `GET /health` is inline on `app`
- **Lifespan:** **None** — no startup/shutdown hooks; Neo4j driver created per-request
- **External systems:** Neo4j (sync driver), `llm-service` (HTTP, optional)
- **Key env vars:** `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `LLM_SERVICE_BASE_URL`, `APP_PORT`
- **Needs router refactor:** Partial — `/health` needs extraction (Step 2e); packaging must be enabled (Step 1)

---

## 4. Route Prefix Map

Every service is mounted under a distinct prefix. The full path seen by external consumers becomes `/<prefix>/<original-path>`.

| Service | Unified prefix | Example old path | Example new path |
|---------|---------------|-----------------|-----------------|
| `llm-service` | `/llm-service` | `POST /llm/complete` | `POST /llm-service/llm/complete` |
| `llm-service` | `/llm-service` | `GET /health` | `GET /llm-service/health` |
| `llm-service` | `/llm-service` | `POST /v1/chat/completions` | `POST /llm-service/v1/chat/completions` |
| `doc_processing` | `/doc-processing` | `POST /documents/pdf-to-markdown` | `POST /doc-processing/documents/pdf-to-markdown` |
| `doc_processing` | `/doc-processing` | `GET /health` | `GET /doc-processing/health` |
| `core_rag_graph` | `/core-rag` | `POST /api/ingest_chunks` | `POST /core-rag/api/ingest_chunks` |
| `core_rag_graph` | `/core-rag` | `GET /health` | `GET /core-rag/health` |
| `ra_literag` | `/ra-literag` | `POST /query` | `POST /ra-literag/query` |
| `ra_literag` | `/ra-literag` | `POST /content/insert` | `POST /ra-literag/content/insert` |
| `temporial_graph` | `/temporal-graph` | `POST /v1/collections` | `POST /temporal-graph/v1/collections` |
| `temporial_graph` | `/temporal-graph` | `POST /v1/rag/answer` (any collection) | `POST /temporal-graph/v1/rag/answer` |
| `temporial_graph_openai` | `/temporal-graph-openai` | `POST /v1/ingest/jobs` | `POST /temporal-graph-openai/v1/ingest/jobs` |
| `temporial_graph_openai` | `/temporal-graph-openai` | `GET /health` | `GET /temporal-graph-openai/health` |
| `temporial_graph_traversal` | `/temporal-graph-traversal` | `POST /query/ask` | `POST /temporal-graph-traversal/query/ask` |
| `temporial_graph_traversal` | `/temporal-graph-traversal` | `GET /health` | `GET /temporal-graph-traversal/health` |
| Unified server | *(root)* | *(new)* | `GET /health` |

> **Note for Cursor agents:** Do not change any router path strings inside the service code. Only the `prefix=` argument on `app.include_router()` in `unified_api/main.py` changes.

---

## 5. Dependency Analysis

### 5.1 Python version

| Service | `requires-python` |
|---------|------------------|
| `core_rag_graph` | `>=3.10` |
| `ra_literag` | `>=3.10` |
| `llm-service` | `>=3.11` |
| `temporial_graph` | `>=3.11` |
| `temporial_graph_traversal` | `>=3.11` |
| `doc_processing` | `>=3.11` |
| `temporial_graph_openai` | **`>=3.12`** ← constraining |

**Unified app requires Python 3.12.** The Docker base image must be `python:3.12-slim`.

### 5.2 Key dependency merge targets

The following packages appear in multiple service `pyproject.toml` files with different version constraints. The unified `pyproject.toml` must satisfy all constraints simultaneously.

| Package | Constraints across services | Unified constraint |
|---------|-----------------------------|--------------------|
| `fastapi` | `==0.104.1` (core_rag_graph), `>=0.115.0` (all others) | `>=0.115.0` — **core_rag_graph must be pinned compat tested** |
| `uvicorn[standard]` | `==0.24.0` (core_rag_graph), `>=0.30.0` / `>=0.32.0` | `>=0.32.0` |
| `pydantic` | `==2.5.0` (core_rag_graph), `>=2.0` / `>=2.8.0` / `>=2.10.0` | `>=2.10.0` — **core_rag_graph must be tested** |
| `neo4j` | `>=5.0.0` (core_rag_graph), `>=5.23.0` (traversal), `>=5.27.0` (tg_openai), **`>=6.1.0`** (tg) | `>=6.1.0` |
| `httpx` | `>=0.27.0` / `>=0.28.0` | `>=0.28.0` |
| `python-dotenv` | `>=1.0.0` / `==1.1.1` | `>=1.0.1` |
| `pyyaml` | `>=6.0` / `>=6.0.1` / `>=6.0.2` | `>=6.0.2` |
| `starlette` | implied by fastapi | `>=0.40.0` (fastapi 0.115 already pins this) |

> **Warning for Cursor agents:** `core_rag_graph` pins `fastapi==0.104.1` and `pydantic==2.5.0`. These exact pins will be overridden by the unified constraint. After merging, run `core_rag_graph`'s route functions in the unified server and ensure none break due to the fastapi/pydantic version bump. If they do, update the affected route handler code in `core_rag_graph/`.

### 5.3 System packages (for Dockerfile)

Union of all services' `apt-get install` requirements:

```
ffmpeg libglib2.0-0 libsm6 libxrender1 libxext6 libxcb1 libgomp1 libgl1
```

All of these come from `doc_processing/Dockerfile.compose`.

---

## 6. Pre-conditions and Setup

Before starting any implementation step, verify:

1. The working directory for all commands is `/media/prashanth/extmnt1/common` (the repo root).
2. `uv` is installed (`uv --version`).
3. Docker with BuildKit is available (`docker buildx version`).
4. All per-service `.env` files exist (at minimum `llm-service/.env` and `doc_processing/.env`).
5. The repo-root `.env` exists and contains `NEO4J_PASSWORD` and `POSTGRES_PASSWORD`.

---

## Step 1 — Enable packaging for `temporial_graph_traversal`

**Why:** `temporial_graph_traversal/pyproject.toml` has `[tool.uv] package = false`, which means `uv` treats it as a non-installable script collection. The unified `pyproject.toml` needs to import it as a Python package. This step enables that.

**File to edit:** `temporial_graph_traversal/pyproject.toml`

**Change:** Remove the line `package = false` from `[tool.uv]`. If `[tool.uv]` becomes empty, remove the section entirely.

**Before:**
```toml
[tool.uv]
package = false
```

**After:** *(section removed entirely)*

**Then add a build system block** if one does not already exist in `temporial_graph_traversal/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.26.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

**Verify:** Run `uv build` inside `temporial_graph_traversal/` — it should produce a wheel without errors.

**Also create** `temporial_graph_traversal/app/__init__.py` if it does not already exist (empty file):

```bash
touch /media/prashanth/extmnt1/common/temporial_graph_traversal/app/__init__.py
```

**Do not change any other file in this service.**

---

## Step 2 — Refactor inline routes to `APIRouter` (three services + two partial)

### Why this step is needed

FastAPI's `app.include_router(router, prefix="/foo")` only works with `APIRouter` objects. Three services (`core_rag_graph`, `ra_literag`, `temporial_graph`) define all routes directly on `app`, and two services (`temporial_graph_openai`, `temporial_graph_traversal`) have a single inline `/health` route. These must be moved to `APIRouter` objects so they can be mounted in the unified app.

> **Important for Cursor agents:** Do **not** change any route path strings, request models, response models, or handler logic in this step. The only changes are:
> - Replace `@app.get(...)` → `@router.get(...)` etc.
> - Add `router = APIRouter()` at the top of each new file.
> - Add `app.include_router(router)` calls in the service's own `main.py` / `graph_server.py`.
> - The service must still run standalone via `uvicorn` on its original port — verify this after each sub-step.

---

### Step 2a — `core_rag_graph` router extraction

**Files to create:**

#### `core_rag_graph/routers/__init__.py`
Empty file.

#### `core_rag_graph/routers/health.py`

Move these two routes from `graph_server.py` (currently at lines ~971–981):

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "core-rag-graph"}


@router.get("/health/ready")
async def health_ready():
    return {"status": "ready"}
```

#### `core_rag_graph/routers/graph_api.py`

Create this file. At the top:

```python
from fastapi import APIRouter, HTTPException, WebSocket
# ... copy all other imports that the route handlers in graph_server.py use ...

router = APIRouter()
```

Move **all** `@app.post`, `@app.get`, `@app.delete` routes that start with `/api/` from `graph_server.py` into this file. Replace every `@app.` with `@router.`. The complete list of routes to move (by path):

```
POST   /api/extrac_graph_data
POST   /api/ingest_chunks
POST   /api/generate_community_reports
POST   /api/get_community_reports
POST   /api/delete_file
POST   /api/delete_collection
DELETE /api/collections/{collection_id}
POST   /api/delete_kb
POST   /api/test_post
POST   /api/get_kb_graph_data
POST   /api/retrieve
POST   /api/query
POST   /api/get-or-create-collection
POST   /api/get-collection-metadata-by-collection-id
GET    /api/get-all-collections
GET    /api/collections
GET    /api/collections/{collection_id}
POST   /api/collections/get-or-create
POST   /api/collections
GET    /api/metrics
POST   /api/getOrCreateCollection
POST   /api/getCollectionMetadataByCollectionId
GET    /api/getAllColecctions
GET    /api/test
```

All global variables these handlers reference (`GRAPH_REPOSITORY`, `RUNTIME_METRICS`, `CONFIG`, `active_connections`, etc.) must remain in `graph_server.py` and be imported into `graph_api.py`:

```python
# At the top of graph_api.py, after the router = APIRouter() line:
from graph_server import GRAPH_REPOSITORY, RUNTIME_METRICS, CONFIG, active_connections
```

> **Note:** This creates a circular-ish import only if `graph_server.py` imports from `graph_api.py` and `graph_api.py` imports from `graph_server.py`. To avoid this, move the global variables to a separate `core_rag_graph/state.py` module and import from there in both files.

**Recommended refactor to avoid circular imports:**

1. Create `core_rag_graph/state.py`:
```python
# state.py — holds module-level mutable state
import os
from graph.config import get_config
from graph.utils.graph_repository import (
    NetworkXJsonGraphRepository, Neo4jGraphRepository,
    DualWriteGraphRepository, GraphRepository,
)

CONFIG = get_config()
RUNTIME_METRICS = {
    "ingest_latency_ms_total": 0.0,
    "ingest_requests_total": 0,
    "query_latency_ms_total": 0.0,
    "query_requests_total": 0,
}

def _create_graph_repository() -> GraphRepository:
    # ... copy the full function body from graph_server.py ...
    pass

GRAPH_REPOSITORY: GraphRepository = _create_graph_repository()
active_connections: dict = {}
```

2. In `graph_server.py`, replace the variable definitions with imports from `state.py`:
```python
from state import GRAPH_REPOSITORY, RUNTIME_METRICS, CONFIG, active_connections
```

3. In `graph_api.py`, import from `state.py` too:
```python
from state import GRAPH_REPOSITORY, RUNTIME_METRICS, CONFIG, active_connections
```

**Edit `core_rag_graph/graph_server.py`:**

Replace the `@app.on_event("shutdown")` block with a lifespan context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    yield
    # Shutdown
    from state import GRAPH_REPOSITORY
    GRAPH_REPOSITORY.close()

app = FastAPI(title="graph Unified Interface", version="1.0.0", lifespan=lifespan)
```

Add router includes after the middleware registrations:

```python
from routers.health import router as health_router
from routers.graph_api import router as graph_api_router

app.include_router(health_router)
app.include_router(graph_api_router)
```

**Standalone verification:**
```bash
cd /media/prashanth/extmnt1/common/core_rag_graph
uv run uvicorn graph_server:app --port 20050 --reload
curl http://localhost:20050/health          # must return {"status": "ok"}
curl http://localhost:20050/api/collections  # must return list
```

---

### Step 2b — `ra_literag` router extraction

**Files to create:**

#### `ra_literag/app/routers/__init__.py`
Empty file.

#### `ra_literag/app/routers/health.py`

Move routes tagged `health` from `app/main.py`:

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    return {"status": "ready"}
```

#### `ra_literag/app/routers/config.py`

Move routes tagged `config`. These reference `_rag_cache`, `get_rag()`, `db_config`, and `WorkspaceConfigPayload`. Import them from `app.main` or `app.config`:

```python
from fastapi import APIRouter, HTTPException
from app.workspace_config import WorkspaceConfigPayload, merge_workspace_config
# Import shared state from main (or move to a state module)
from app.main import _rag_cache, get_rag
import app.db_config as db_config

router = APIRouter(tags=["config"])

# Move @app.get("/config"), @app.get("/config/{workspace_id}"),
# @app.post("/config/{workspace_id}") here
# Replace @app. with @router.
```

#### `ra_literag/app/routers/query.py`

Move routes tagged `query`:

```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from app.main import _rag_cache, get_rag

router = APIRouter(tags=["query"])

# Move @app.post("/query"), @app.post("/query/multimodal") here
```

#### `ra_literag/app/routers/ingest.py`

Move routes tagged `ingest`:

```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.main import _rag_cache, get_rag

router = APIRouter(tags=["ingest"])

# Move @app.post("/content/insert"), @app.post("/documents/process") here
```

**Edit `ra_literag/app/main.py`:**

Remove the inline route definitions and add includes:

```python
from app.routers.health import router as health_router
from app.routers.config import router as config_router
from app.routers.query  import router as query_router
from app.routers.ingest import router as ingest_router

# After app = FastAPI(...) line:
app.include_router(health_router)
app.include_router(config_router)
app.include_router(query_router)
app.include_router(ingest_router)
```

> **Circular import note:** `config.py`, `query.py`, `ingest.py` all need `_rag_cache` and `get_rag` from `app/main.py`, but `app/main.py` will import from those routers. To break the cycle, move `_rag_cache` and `get_rag` to a new module `ra_literag/app/rag_cache.py` and import from there in all files.

**Create `ra_literag/app/rag_cache.py`:**

```python
"""Shared in-memory RAG instance cache and factory."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raganything import RAGAnything

_rag_cache: dict[str, "RAGAnything"] = {}


async def get_rag(workspace: str, db_overrides: dict | None = None) -> "RAGAnything":
    # Move the full get_rag() function body here from app/main.py
    ...
```

Then in `app/main.py`, `app/routers/config.py`, `app/routers/query.py`, `app/routers/ingest.py`, import as:

```python
from app.rag_cache import _rag_cache, get_rag
```

**Standalone verification:**
```bash
cd /media/prashanth/extmnt1/common/ra_literag
uv run uvicorn app.main:app --port 8000 --reload
curl http://localhost:8000/health
curl http://localhost:8000/config
```

---

### Step 2c — `temporial_graph` router extraction

**Files to create:**

#### `temporial_graph/src/temporial_graph_rag/api/routers/__init__.py`
Empty file.

#### `temporial_graph/src/temporial_graph_rag/api/routers/health.py`

Move the health routes:

```python
from fastapi import APIRouter, Request
from temporial_graph_rag.graph import Neo4jGraphStore
from temporial_graph_rag.llm import LLMClient, LLMServiceConfig

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/v1/health/llm")
async def health_llm():
    # Copy the handler body from main.py
    ...


@router.get("/v1/health/neo4j")
async def health_neo4j(request: Request):
    # Copy the handler body from main.py
    ...
```

#### `temporial_graph/src/temporial_graph_rag/api/routers/collections.py`

Move all `/v1/collections*` routes.

#### `temporial_graph/src/temporial_graph_rag/api/routers/search.py`

Move all snapshot, events, impact-prior, `/v1/.../rag/answer`, `/v1/.../rag/multi_step` routes.

#### `temporial_graph/src/temporial_graph_rag/api/routers/ingest.py`

Move `/v1/ingest/chunks` and `/v1/ingest/chunks/process`.

#### `temporial_graph/src/temporial_graph_rag/api/routers/network.py`

Move `/v1/network/entities/{entity_name}/collections`.

> **Dependency injection note:** Many handlers in `temporial_graph/api/main.py` use `Depends(get_neo4j_store)`, `Depends(get_registry)`, etc., which read from `request.app.state`. These dependency functions live in `main.py`. Move them to `temporial_graph/src/temporial_graph_rag/api/dependencies.py` and import from there in both `main.py` and each router file.

**Create `temporial_graph/src/temporial_graph_rag/api/dependencies.py`:**

```python
from fastapi import Request
from temporial_graph_rag.graph import Neo4jGraphStore
from temporial_graph_rag.collections.registry import MutableCollectionRegistry


def get_neo4j_store(request: Request) -> Neo4jGraphStore | None:
    return getattr(request.app.state, "neo4j_store", None)


def get_registry(request: Request) -> MutableCollectionRegistry:
    return request.app.state.registry
```

**Edit `temporial_graph/src/temporial_graph_rag/api/main.py`:**

Replace inline routes with includes:

```python
from temporial_graph_rag.api.routers import health, collections, search, ingest, network

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(search.router)
app.include_router(ingest.router)
app.include_router(network.router)
```

**Standalone verification:**
```bash
cd /media/prashanth/extmnt1/common/temporial_graph
uv run uvicorn temporial_graph_rag.api.main:app --app-dir src --port 8082 --reload
curl http://localhost:8082/health
curl http://localhost:8082/v1/collections
```

---

### Step 2d — `temporial_graph_openai` health route extraction

The `/health` route in `temporial_graph_openai/temporal_graph/api/main.py` is the only inline route in this service. Extract it.

**Create `temporial_graph_openai/temporal_graph/api/health_routes.py`:**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

**Edit `temporial_graph_openai/temporal_graph/api/main.py`:**

Remove the inline `@app.get("/health")` handler and add:

```python
from temporal_graph.api.health_routes import router as health_router
app.include_router(health_router)
```

---

### Step 2e — `temporial_graph_traversal` health route extraction

Same pattern as 2d.

**Create `temporial_graph_traversal/app/api/health_routes.py`:**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

**Edit `temporial_graph_traversal/app/main.py`:**

Remove the inline `@app.get("/health")` handler and add:

```python
from app.api.health_routes import router as health_router
app.include_router(health_router)
```

---

## Step 3 — Create `unified_api/` skeleton

Create the `unified_api/` directory at the repo root with placeholder files. All placeholder content will be filled in Steps 4–7.

```
/media/prashanth/extmnt1/common/unified_api/
├── __init__.py
├── main.py
├── lifespan.py
├── settings.py
├── Dockerfile.compose       (created in Step 8)
├── .dockerignore            (created in Step 8)
└── logs/
    └── .gitkeep
```

**`unified_api/__init__.py`** — empty file.

**`unified_api/logs/.gitkeep`** — empty file (tracks the logs directory in git).

**`unified_api/main.py`** (placeholder, to be completed in Step 7):

```python
"""Unified FastAPI application — entry point for all merged services."""
from __future__ import annotations

from fastapi import FastAPI

from unified_api.lifespan import lifespan

app = FastAPI(
    title="Unified API",
    description="All services unified: llm-service, doc-processing, core-rag-graph, ra-literag, temporal-graph, temporal-graph-openai, temporal-graph-traversal.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "unified-api"}


# TODO: include_router calls will be added in Step 7
```

**`unified_api/lifespan.py`** (placeholder, to be completed in Step 6):

```python
"""Merged lifespan: runs all services' startup and shutdown in dependency order."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: startup — filled in Step 6
    logger.info("unified-api startup complete")
    yield
    # TODO: shutdown — filled in Step 6
    logger.info("unified-api shutdown complete")
```

**`unified_api/settings.py`** (placeholder, to be completed in Step 5):

```python
"""Unified settings — documents all env vars used across all merged services."""
from __future__ import annotations
```

---

## Step 4 — Create `unified_api/pyproject.toml`

Create `unified_api/pyproject.toml` with the merged dependency set. This file references all seven services as local path dependencies so their packages are importable.

**File:** `unified_api/pyproject.toml`

```toml
[project]
name = "unified-api"
version = "0.1.0"
description = "All FastAPI services merged into a single process."
readme = "README.md"
requires-python = ">=3.12"

dependencies = [
    # ── Web framework ──────────────────────────────────────────────
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "starlette>=0.40.0",
    "python-multipart>=0.0.9",
    "sse-starlette>=2.1.0",

    # ── Settings / config ──────────────────────────────────────────
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "python-dotenv>=1.0.1",
    "pyyaml>=6.0.2",

    # ── HTTP clients ───────────────────────────────────────────────
    "httpx>=0.28.0",
    "requests>=2.32.5",

    # ── LLM / AI ───────────────────────────────────────────────────
    "litellm>=1.82.4",
    "openai>=1.59.0",

    # ── Graph DB ───────────────────────────────────────────────────
    "neo4j>=6.1.0",

    # ── Relational DB ──────────────────────────────────────────────
    "asyncpg>=0.29.0",

    # ── Vector DB ──────────────────────────────────────────────────
    # (chroma client used by ra_literag via lightrag)

    # ── RAG framework ──────────────────────────────────────────────
    "lightrag-hku",
    "huggingface_hub",
    "mineru[core]",
    "tqdm",

    # ── Document processing ────────────────────────────────────────
    "docling[vlm,easyocr,xbrl]>=2.80.0",
    "unstructured[all-docs]",
    "ixbrl-parse",
    "markitdown[all]",
    "lxml>=5",
    "pymupdf>=1.24",
    "mistletoe>=1.3",
    "pandas>=2.0.0",
    "Pillow>=10.0.0",
    "ImageHash>=4.3.2",
    "scikit-learn>=1.5",

    # ── Graph algorithms ───────────────────────────────────────────
    "networkx==3.4.2",
    "graspologic==3.4.4",
    "tiktoken==0.9.0",
    "json-repair==0.46.2",
    "nanoid==2.0.0",
    "websockets==12.0",

    # ── Job queue ──────────────────────────────────────────────────
    "redis[hiredis]>=5.2.0",

    # ── Misc ───────────────────────────────────────────────────────
    "tenacity>=9.0.0",
    "rapidfuzz>=3.11.0",
    "jsonschema>=4.23.0",
    "gunicorn==23.0.0",
    "groq",

    # ── Local service packages (installed as editable) ────────────
    "llm-service",
    "doc-processing",
    "core-rag-graph",
    "ra-literag",
    "temporial-graph-rag",
    "temporal-graph-openai",
    "reference-aware-query-engine",
]

[project.scripts]
unified-api = "unified_api.main:run"

[build-system]
requires = ["hatchling>=1.26.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["unified_api"]

[tool.uv.sources]
llm-service                  = { path = "../llm-service" }
doc-processing               = { path = "../doc_processing" }
core-rag-graph               = { path = "../core_rag_graph" }
ra-literag                   = { path = "../ra_literag" }
temporial-graph-rag          = { path = "../temporial_graph" }
temporal-graph-openai        = { path = "../temporial_graph_openai" }
reference-aware-query-engine = { path = "../temporial_graph_traversal" }

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**After creating this file, run:**

```bash
cd /media/prashanth/extmnt1/common/unified_api
uv lock
```

If `uv lock` reports dependency conflicts, resolve them by adjusting the version constraints in this file. Common conflicts to watch for:

- `fastapi` version incompatibility with `pydantic` version
- `starlette` version incompatibility with `fastapi` version
- `neo4j` major version bump (5 → 6) breaking `core_rag_graph` or `ra_literag`

If any conflict cannot be resolved, pin the conflicting package to the lowest-common version that satisfies all constraints.

---

## Step 5 — Create unified settings module

**File:** `unified_api/settings.py`

This module documents every environment variable across all seven services. Its `UnifiedSettings` class is used only for startup validation — each service still reads env vars through its own `Settings`/`config.py`. This acts as a single reference for operators writing `.env` files.

```python
"""
Unified settings — all env vars used by the unified API.

Each service reads env vars independently through its own config class.
This module serves as a single reference document and as a startup validator.
"""
from __future__ import annotations

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class UnifiedSettings(BaseSettings):
    """All env vars across all merged services. Optional = used by some services only."""

    # ── Shared: Neo4j ─────────────────────────────────────────────────────────
    # Used by: core_rag_graph (NEO4J_USER), ra_literag, temporial_graph,
    #          temporial_graph_openai, temporial_graph_traversal (NEO4J_USERNAME)
    neo4j_uri: str = Field("bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", alias="NEO4J_USER")           # core_rag_graph uses this
    neo4j_username: str = Field("neo4j", alias="NEO4J_USERNAME")   # all others use this
    neo4j_password: str = Field(..., alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")

    # ── Shared: Postgres ──────────────────────────────────────────────────────
    # Used by: ra_literag (workspace config), fin_rag (out of scope)
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_user: str = Field("postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(..., alias="POSTGRES_PASSWORD")
    postgres_database: str = Field("ra_literag", alias="POSTGRES_DATABASE")

    # ── Shared: Chroma ────────────────────────────────────────────────────────
    # Used by: ra_literag
    chroma_host: str = Field("localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(8000, alias="CHROMA_PORT")

    # ── Shared: Ollama ────────────────────────────────────────────────────────
    # Used by: llm-service (OLLAMA_API_BASE), doc_processing (OLLAMA_BASE_URL)
    ollama_api_base: str = Field("http://localhost:11434", alias="OLLAMA_API_BASE")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")

    # ── Shared: LLM service base URL ─────────────────────────────────────────
    # Used by: all services that call llm-service over HTTP.
    # In unified mode set this to http://localhost:8000 (self-reference).
    llm_service_base_url: str = Field("http://localhost:8001", alias="LLM_SERVICE_BASE_URL")

    # ── llm-service ───────────────────────────────────────────────────────────
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    groq_plan: str = Field("FREE", alias="GROQ_PLAN")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    config_dir: Optional[str] = Field(None, alias="CONFIG_DIR")
    litellm_debug: bool = Field(False, alias="LITELLM_DEBUG")

    # ── doc_processing ────────────────────────────────────────────────────────
    doc_processing_temp_dir: Optional[str] = Field(None, alias="DOC_PROCESSING_TEMP_DIR")
    doc_processing_config_dir: Optional[str] = Field(None, alias="DOC_PROCESSING_CONFIG_DIR")

    # ── core_rag_graph ────────────────────────────────────────────────────────
    graph_backend: str = Field("networkx", alias="GRAPH_BACKEND")
    graph_dual_write: bool = Field(False, alias="GRAPH_DUAL_WRITE")
    graph_secondary_backend: str = Field("neo4j", alias="GRAPH_SECONDARY_BACKEND")

    # ── ra_literag ────────────────────────────────────────────────────────────
    lightrag_vector_storage: str = Field("ChromaVectorDBStorage", alias="LIGHTRAG_VECTOR_STORAGE")
    lightrag_graph_storage: str = Field("Neo4JStorage", alias="LIGHTRAG_GRAPH_STORAGE")
    lightrag_kv_storage: str = Field("JsonKVStorage", alias="LIGHTRAG_KV_STORAGE")
    working_dir: Optional[str] = Field(None, alias="WORKING_DIR")

    # ── temporial_graph ───────────────────────────────────────────────────────
    neo4j_enabled: bool = Field(True, alias="NEO4J_ENABLED")
    llm_startup_models_check: bool = Field(False, alias="LLM_STARTUP_MODELS_CHECK")

    # ── temporial_graph_openai ────────────────────────────────────────────────
    job_backend: str = Field("memory", alias="JOB_BACKEND")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    ingest_max_concurrent_jobs: int = Field(4, alias="INGEST_MAX_CONCURRENT_JOBS")

    # ── temporial_graph_traversal ─────────────────────────────────────────────
    collection_aliases: Optional[str] = Field(None, alias="COLLECTION_ALIASES")

    # ── General ───────────────────────────────────────────────────────────────
    debug: bool = Field(False, alias="DEBUG")

    model_config = {"env_file": ".env", "extra": "allow"}


def get_settings() -> UnifiedSettings:
    return UnifiedSettings()
```

---

## Step 6 — Create unified lifespan

**File:** `unified_api/lifespan.py`

This is the most critical file. It runs the startup and shutdown logic from every service in the correct dependency order.

**Startup order** (each service's databases must be ready before it runs):
1. `llm-service` — config-only, no DB connections
2. `doc_processing` — config-only, no DB connections
3. `core_rag_graph` — creates `GraphRepository` (Neo4j or NetworkX)
4. `temporial_graph` — inits Neo4j store and collection registry
5. `temporial_graph_openai` — inits `JobManager`, optional Redis worker, Neo4j schema bootstrap
6. `ra_literag` — inits asyncpg pool (Postgres), preloads workspace RAG instances (Neo4j + Chroma)
7. `temporial_graph_traversal` — no startup action (per-request Neo4j driver)

**Shutdown order** (reverse of startup):
1. `ra_literag` — finalise RAG storages, close asyncpg pool
2. `temporial_graph_openai` — stop Redis worker, close job manager, close Neo4j driver
3. `temporial_graph` — close Neo4j store
4. `core_rag_graph` — close graph repository
5. `llm-service`, `doc_processing` — no teardown

```python
"""Unified lifespan — startup and shutdown for all merged services."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ── llm-service ───────────────────────────────────────────────────────────────

def _startup_llm_service(app: FastAPI) -> None:
    """Apply LiteLLM env and configure logging. Mirrors create_app() in llm_service/main.py."""
    try:
        from llm_service.config import apply_litellm_env, get_settings as llm_get_settings
        from llm_service.logging_setup import configure_litellm_debug, configure_logging
        settings = llm_get_settings()
        verbose = settings.debug or settings.litellm_debug
        configure_logging(debug=verbose)
        configure_litellm_debug(enabled=verbose)
        apply_litellm_env(settings)
        logger.info("[llm-service] startup complete")
    except Exception as exc:
        logger.warning("[llm-service] startup failed (non-fatal): %s", exc)


# ── doc_processing ────────────────────────────────────────────────────────────

def _startup_doc_processing(app: FastAPI) -> None:
    """Configure debug logging. Mirrors lifespan in doc_processing/main.py."""
    try:
        from doc_processing.debug_trace import configure_debug_logging
        configure_debug_logging()
        logger.info("[doc_processing] startup complete")
    except Exception as exc:
        logger.warning("[doc_processing] startup failed (non-fatal): %s", exc)


# ── core_rag_graph ────────────────────────────────────────────────────────────

def _startup_core_rag_graph(app: FastAPI) -> None:
    """
    core_rag_graph creates GRAPH_REPOSITORY at module import time (in state.py).
    Nothing additional to do here; just verify the import works.
    Store a reference on app.state for the shutdown handler.
    """
    try:
        from state import GRAPH_REPOSITORY  # imported from core_rag_graph/state.py
        app.state.crg_graph_repository = GRAPH_REPOSITORY
        logger.info("[core_rag_graph] startup complete (backend=%s)", type(GRAPH_REPOSITORY).__name__)
    except Exception as exc:
        logger.warning("[core_rag_graph] startup failed (non-fatal): %s", exc)


def _shutdown_core_rag_graph(app: FastAPI) -> None:
    repo = getattr(app.state, "crg_graph_repository", None)
    if repo is not None:
        try:
            repo.close()
            logger.info("[core_rag_graph] shutdown complete")
        except Exception as exc:
            logger.warning("[core_rag_graph] shutdown error: %s", exc)


# ── temporial_graph ───────────────────────────────────────────────────────────

def _startup_temporial_graph(app: FastAPI) -> None:
    """
    Mirrors lifespan in temporial_graph/src/temporial_graph_rag/api/main.py.
    Inits Neo4j store and sets the collection registry backend.
    """
    try:
        import os
        from temporial_graph_rag.graph import Neo4jGraphStore, Neo4jSettings
        from temporial_graph_rag.collections.registry import (
            CollectionRegistry, MutableCollectionRegistry, Neo4jCollectionRegistry,
        )

        neo4j_settings = Neo4jSettings.from_env()
        if neo4j_settings.enabled:
            store = Neo4jGraphStore(neo4j_settings)
            app.state.tg_neo4j_store = store
            app.state.tg_registry = MutableCollectionRegistry(Neo4jCollectionRegistry(store))
        else:
            app.state.tg_neo4j_store = None
            app.state.tg_registry = MutableCollectionRegistry(CollectionRegistry())

        # Optional LLM startup probe
        if os.getenv("LLM_STARTUP_MODELS_CHECK", "").strip().lower() in ("1", "true", "yes"):
            try:
                from temporial_graph_rag.llm import LLMClient, LLMServiceConfig
                cfg = LLMServiceConfig.from_env()
                probe = LLMClient(cfg)
                try:
                    probe.models()
                finally:
                    probe.close()
            except Exception as probe_exc:
                logger.warning("[temporial_graph] LLM probe failed: %s", probe_exc)

        logger.info("[temporial_graph] startup complete")
    except Exception as exc:
        logger.warning("[temporial_graph] startup failed (non-fatal): %s", exc)


def _shutdown_temporial_graph(app: FastAPI) -> None:
    store = getattr(app.state, "tg_neo4j_store", None)
    if store is not None:
        try:
            store.close()
            logger.info("[temporial_graph] shutdown complete")
        except Exception as exc:
            logger.warning("[temporial_graph] shutdown error: %s", exc)


# ── temporial_graph_openai ────────────────────────────────────────────────────

async def _startup_temporial_graph_openai(app: FastAPI) -> None:
    """
    Mirrors lifespan in temporial_graph_openai/temporal_graph/api/main.py.
    Creates JobManager, optional Redis worker, bootstraps Neo4j schema.
    """
    try:
        import asyncio
        from temporal_graph.jobs.manager import JobManager, ingest_worker_loop
        from temporal_graph.neo4j.bootstrap import bootstrap_graph
        from temporal_graph.neo4j.driver import get_driver
        from temporal_graph.settings import get_settings as tgo_get_settings

        settings = tgo_get_settings()
        app.state.tgo_settings = settings
        app.state.tgo_job_manager = JobManager(settings)
        app.state.tgo_worker_stop = asyncio.Event()
        app.state.tgo_worker_task = None

        if (
            (settings.job_backend or "").strip().lower() == "redis"
            and settings.ingest_start_redis_worker
            and settings.redis_url
        ):
            app.state.tgo_worker_task = asyncio.create_task(
                ingest_worker_loop(app, app.state.tgo_worker_stop)
            )
            logger.info("[temporial_graph_openai] Redis ingest worker started")

        driver = get_driver(settings)
        app.state.tgo_neo4j_driver = driver
        try:
            await bootstrap_graph(driver, settings)
        except Exception as bootstrap_exc:
            logger.warning("[temporial_graph_openai] Neo4j bootstrap failed: %s", bootstrap_exc)

        logger.info("[temporial_graph_openai] startup complete")
    except Exception as exc:
        logger.warning("[temporial_graph_openai] startup failed (non-fatal): %s", exc)


async def _shutdown_temporial_graph_openai(app: FastAPI) -> None:
    worker_stop = getattr(app.state, "tgo_worker_stop", None)
    if worker_stop is not None:
        worker_stop.set()
    worker_task = getattr(app.state, "tgo_worker_task", None)
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except Exception:
            pass
    job_manager = getattr(app.state, "tgo_job_manager", None)
    if job_manager is not None:
        try:
            await job_manager.close()
        except Exception:
            pass
    driver = getattr(app.state, "tgo_neo4j_driver", None)
    if driver is not None:
        try:
            from temporal_graph.neo4j.driver import close_driver
            from temporal_graph.settings import get_settings as tgo_get_settings
            await close_driver(tgo_get_settings())
        except Exception as exc:
            logger.warning("[temporial_graph_openai] Neo4j driver close error: %s", exc)
    logger.info("[temporial_graph_openai] shutdown complete")


# ── ra_literag ────────────────────────────────────────────────────────────────

async def _startup_ra_literag(app: FastAPI) -> None:
    """
    Mirrors lifespan in ra_literag/app/main.py.
    Inits asyncpg pool, then preloads workspace RAG instances.
    """
    try:
        from app import db_config as ra_db_config
        from app.rag_cache import get_rag  # created in Step 2b

        await ra_db_config.init_pool()
        for workspace_id in await ra_db_config.list_workspace_ids():
            try:
                await get_rag(workspace_id)
            except Exception:
                pass
        app.state.ra_literag_db_config = ra_db_config
        logger.info("[ra_literag] startup complete")
    except Exception as exc:
        logger.warning("[ra_literag] startup failed (non-fatal): %s", exc)


async def _shutdown_ra_literag(app: FastAPI) -> None:
    try:
        from app.rag_cache import _rag_cache
        from app import db_config as ra_db_config
        for rag in list(_rag_cache.values()):
            try:
                await rag.finalize_storages()
            except Exception:
                pass
        _rag_cache.clear()
        await ra_db_config.close_pool()
        logger.info("[ra_literag] shutdown complete")
    except Exception as exc:
        logger.warning("[ra_literag] shutdown error: %s", exc)


# ── Main lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup (dependency order) ───────────────────────────────────────────
    _startup_llm_service(app)
    _startup_doc_processing(app)
    _startup_core_rag_graph(app)
    _startup_temporial_graph(app)
    await _startup_temporial_graph_openai(app)
    await _startup_ra_literag(app)
    # temporial_graph_traversal: no startup action

    logger.info("unified-api startup complete — all services initialised")
    yield

    # ── Shutdown (reverse order) ─────────────────────────────────────────────
    await _shutdown_ra_literag(app)
    await _shutdown_temporial_graph_openai(app)
    _shutdown_temporial_graph(app)
    _shutdown_core_rag_graph(app)
    # llm-service, doc_processing: no teardown

    logger.info("unified-api shutdown complete")
```

---

## Step 7 — Wire all routers into `unified_api/main.py`

Replace the placeholder `unified_api/main.py` from Step 3 with the full implementation.

**Important import notes for Cursor agents:**
- Services with `src/` layout are imported by their package name (e.g. `from llm_service.routers import health`).
- `core_rag_graph` has no `src/` — its packages are at the repo root (`graph/`, `routers/`). The `uv` local path dependency installs them into the virtual env.
- `ra_literag` packages are `app.*` and `raganything.*` — both installed by the local path dependency.
- `temporial_graph_traversal` packages are `app.*` (enabled in Step 1).

```python
"""Unified FastAPI application — entry point for all merged services."""
from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from unified_api.lifespan import lifespan

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unified API",
    description=(
        "All services in one process: llm-service, doc-processing, core-rag-graph, "
        "ra-literag, temporal-graph, temporal-graph-openai, temporal-graph-traversal."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Global CORS middleware ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Unified health probe ───────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "unified-api"}


# ── llm-service ───────────────────────────────────────────────────────────────
try:
    from llm_service.routers import health as llm_health, llm as llm_llm, openai as llm_openai
    app.include_router(llm_health.router,  prefix="/llm-service", tags=["llm-service:health"])
    app.include_router(llm_llm.router,     prefix="/llm-service", tags=["llm-service:llm"])
    app.include_router(llm_openai.router,  prefix="/llm-service", tags=["llm-service:openai"])
    logger.info("Mounted llm-service routers at /llm-service")
except ImportError as e:
    logger.error("Failed to mount llm-service routers: %s", e)


# ── doc_processing ────────────────────────────────────────────────────────────
try:
    from doc_processing.routers import health as dp_health, documents as dp_documents
    app.include_router(dp_health.router,     prefix="/doc-processing", tags=["doc-processing:health"])
    app.include_router(dp_documents.router,  prefix="/doc-processing", tags=["doc-processing:documents"])
    logger.info("Mounted doc_processing routers at /doc-processing")
except ImportError as e:
    logger.error("Failed to mount doc_processing routers: %s", e)


# ── core_rag_graph ────────────────────────────────────────────────────────────
try:
    from routers import health as crg_health, graph_api as crg_graph_api
    from graph.utils.collection_id_middleware import CollectionIdMiddleware
    app.add_middleware(CollectionIdMiddleware)
    app.include_router(crg_health.router,    prefix="/core-rag", tags=["core-rag:health"])
    app.include_router(crg_graph_api.router, prefix="/core-rag", tags=["core-rag:api"])
    logger.info("Mounted core_rag_graph routers at /core-rag")
except ImportError as e:
    logger.error("Failed to mount core_rag_graph routers: %s", e)


# ── ra_literag ────────────────────────────────────────────────────────────────
try:
    from app.routers import (
        health as ral_health,
        config as ral_config,
        query as ral_query,
        ingest as ral_ingest,
    )
    app.include_router(ral_health.router,  prefix="/ra-literag", tags=["ra-literag:health"])
    app.include_router(ral_config.router,  prefix="/ra-literag", tags=["ra-literag:config"])
    app.include_router(ral_query.router,   prefix="/ra-literag", tags=["ra-literag:query"])
    app.include_router(ral_ingest.router,  prefix="/ra-literag", tags=["ra-literag:ingest"])
    logger.info("Mounted ra_literag routers at /ra-literag")
except ImportError as e:
    logger.error("Failed to mount ra_literag routers: %s", e)


# ── temporial_graph ───────────────────────────────────────────────────────────
try:
    from temporial_graph_rag.api.routers import (
        health as tg_health,
        collections as tg_collections,
        search as tg_search,
        ingest as tg_ingest,
        network as tg_network,
    )
    from temporial_graph_rag.api.collection_name_middleware import CollectionNameExposeMiddleware
    app.add_middleware(CollectionNameExposeMiddleware)
    app.include_router(tg_health.router,      prefix="/temporal-graph", tags=["temporal-graph:health"])
    app.include_router(tg_collections.router, prefix="/temporal-graph", tags=["temporal-graph:collections"])
    app.include_router(tg_search.router,      prefix="/temporal-graph", tags=["temporal-graph:search"])
    app.include_router(tg_ingest.router,      prefix="/temporal-graph", tags=["temporal-graph:ingest"])
    app.include_router(tg_network.router,     prefix="/temporal-graph", tags=["temporal-graph:network"])
    logger.info("Mounted temporial_graph routers at /temporal-graph")
except ImportError as e:
    logger.error("Failed to mount temporial_graph routers: %s", e)


# ── temporial_graph_openai ────────────────────────────────────────────────────
try:
    from temporal_graph.api.health_routes   import router as tgo_health_router
    from temporal_graph.api.ingest_routes   import router as tgo_ingest_router
    from temporal_graph.api.retrieve_routes import router as tgo_retrieve_router
    from temporal_graph.api.collection_routes import router as tgo_collection_router
    from temporal_graph.middleware.collection_wire import (
        CollectionPathRewriteMiddleware,
        CollectionWireResponseMiddleware,
    )
    app.add_middleware(CollectionWireResponseMiddleware)
    app.add_middleware(CollectionPathRewriteMiddleware)
    app.include_router(tgo_health_router,     prefix="/temporal-graph-openai", tags=["temporal-graph-openai:health"])
    app.include_router(tgo_ingest_router,     prefix="/temporal-graph-openai", tags=["temporal-graph-openai:ingest"])
    app.include_router(tgo_retrieve_router,   prefix="/temporal-graph-openai", tags=["temporal-graph-openai:retrieve"])
    app.include_router(tgo_collection_router, prefix="/temporal-graph-openai", tags=["temporal-graph-openai:collections"])
    logger.info("Mounted temporial_graph_openai routers at /temporal-graph-openai")
except ImportError as e:
    logger.error("Failed to mount temporial_graph_openai routers: %s", e)


# ── temporial_graph_traversal ─────────────────────────────────────────────────
try:
    from app.api.health_routes    import router as tgt_health_router
    from app.api.query_routes     import router as tgt_query_router
    from app.api.collection_routes import router as tgt_collection_router
    # Note: app.api here refers to temporial_graph_traversal/app/api/ not ra_literag/app/
    # This is disambiguated by Python's package import system after uv installs both.
    # If import collisions occur, use importlib.import_module() with the full path.
    app.include_router(tgt_health_router,     prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal:health"])
    app.include_router(tgt_query_router,      prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal:query"])
    app.include_router(tgt_collection_router, prefix="/temporal-graph-traversal", tags=["temporal-graph-traversal:collections"])
    logger.info("Mounted temporial_graph_traversal routers at /temporal-graph-traversal")
except ImportError as e:
    logger.error("Failed to mount temporial_graph_traversal routers: %s", e)


def run() -> None:
    import uvicorn
    uvicorn.run("unified_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
```

> **Import collision warning:** Both `ra_literag` and `temporial_graph_traversal` use `app.*` as their package namespace. After `uv` installs them both as local path dependencies, Python may see only one of them as `app`. To resolve this, the `[tool.hatch.build.targets.wheel] packages` in both services' `pyproject.toml` must use distinct names. For `temporial_graph_traversal`, rename the wheel package from `app` to `raqe` by adding this to its `pyproject.toml`:
>
> ```toml
> [tool.hatch.build.targets.wheel]
> packages = ["app"]
> sources = {"app" = "raqe"}
> ```
>
> Then all imports of `temporial_graph_traversal`'s app code use `raqe.*` instead of `app.*`. Update all internal imports in `temporial_graph_traversal/` accordingly.
>
> **Alternative approach** if renaming is too invasive: use `sys.path` insertion in `lifespan.py` and `main.py` to explicitly scope per-service directories before importing. Add this at the top of `unified_api/main.py`:
>
> ```python
> import sys, os
> # Ensure correct resolution order for services with conflicting package names
> _REPO = os.path.dirname(os.path.dirname(__file__))
> sys.path.insert(0, os.path.join(_REPO, "ra_literag"))         # app.* → ra_literag
> # temporial_graph_traversal uses separate raqe package name (see Step 1 / above)
> ```

---

## Step 8 — Create `unified_api/Dockerfile.compose`

**File:** `unified_api/Dockerfile.compose`

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL service="unified-api"

WORKDIR /repo

# System packages (union of all services — primarily from doc_processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libxcb1 \
        libgomp1 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Layer 1: copy only lockfiles (cache dependency installation) ──────────────
COPY unified_api/pyproject.toml unified_api/uv.lock ./unified_api/
# Service pyproject files (needed by uv for local path resolution)
COPY core_rag_graph/pyproject.toml          ./core_rag_graph/
COPY doc_processing/pyproject.toml          ./doc_processing/
COPY llm-service/pyproject.toml             ./llm-service/
COPY ra_literag/pyproject.toml              ./ra_literag/
COPY temporial_graph/pyproject.toml         ./temporial_graph/
COPY temporial_graph_openai/pyproject.toml  ./temporial_graph_openai/
COPY temporial_graph_traversal/pyproject.toml ./temporial_graph_traversal/

WORKDIR /repo/unified_api

# Install deps (no project source yet — maximises cache hit on dependency layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ── Layer 2: copy full source ─────────────────────────────────────────────────
WORKDIR /repo
COPY . .

WORKDIR /repo/unified_api

# Install the project itself (source is now present)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", \
    "mkdir -p /repo/unified_api/logs && \
     set -o pipefail && \
     uv run uvicorn unified_api.main:app \
       --host 0.0.0.0 --port 8000 \
       --workers 1 \
       2>&1 | tee -a /repo/unified_api/logs/uvicorn.log"]
```

**File:** `unified_api/.dockerignore`

```
# Per-service virtual environments and caches
**/.venv/
**/__pycache__/
**/*.pyc
**/*.pyo

# Logs (bind-mounted at runtime)
**/logs/*.log
**/logs/

# Temp and generated data
**/data/temp/
**/.env
**/*.egg-info/

# Test artefacts
**/.pytest_cache/
**/htmlcov/
**/.coverage

# Git
**/.git/
**/.gitignore
```

---

## Step 9 — Update `docker-compose.yml`

**Remove** these service definitions entirely from `docker-compose.yml`:
- `doc_processing`
- `llm-service`
- `core_rag_graph`
- `ra_literag`
- `temporial_graph`
- `temporial_graph_openai`
- `temporial_graph_traversal`

**Keep unchanged:**
- `postgres`
- `neo4j`
- `chroma`
- `ollama`
- `ollama_init`
- `fin_rag_migrate`
- `fin_rag`

**Add the new `unified_api` service** in place of the removed services:

```yaml
  unified_api:
    build:
      context: .
      dockerfile: unified_api/Dockerfile.compose
    container_name: unified-api
    env_file:
      - .env
    environment:
      # ── Neo4j (shared by all graph services) ──────────────────────────────
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USERNAME:-neo4j}
      NEO4J_USERNAME: ${NEO4J_USERNAME:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      NEO4J_DATABASE: neo4j
      NEO4J_ENABLED: "true"
      # ── Postgres ──────────────────────────────────────────────────────────
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DATABASE: ${POSTGRES_DB_RA_LITERAG:-ra_literag}
      # ── Chroma ────────────────────────────────────────────────────────────
      CHROMA_HOST: chroma
      CHROMA_PORT: "8000"
      LIGHTRAG_VECTOR_STORAGE: ChromaVectorDBStorage
      LIGHTRAG_GRAPH_STORAGE: Neo4JStorage
      # ── Ollama ────────────────────────────────────────────────────────────
      OLLAMA_API_BASE: http://ollama:11434
      OLLAMA_BASE_URL: http://ollama:11434
      # ── LLM service (self-reference: unified server calls its own /llm-service routes) ──
      LLM_SERVICE_BASE_URL: http://localhost:8000/llm-service
      # ── Logging ───────────────────────────────────────────────────────────
      FIN_RAG_LOG_DIR: /app/logs
    volumes:
      - ./unified_api/logs:/app/logs
      - ./db/core_rag_graph/data:/repo/core_rag_graph/data
      - ./doc_processing/data/temp:/repo/doc_processing/data/temp
      - ./db/ra_literag_data:/repo/ra_literag/rag_storage
    ports:
      - "8000:8000"
    depends_on:
      neo4j:
        condition: service_healthy
      postgres:
        condition: service_healthy
      chroma:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 60s
    restart: unless-stopped
```

**Also update `fin_rag`'s `depends_on`** since `llm-service` no longer exists as a separate service:

```yaml
  fin_rag:
    ...
    depends_on:
      fin_rag_migrate:
        condition: service_completed_successfully
      unified_api:           # ← was: llm-service
        condition: service_healthy
      postgres:
        condition: service_healthy
      chroma:
        condition: service_healthy
```

---

## Step 10 — Update `docker-compose-test.yaml`

Apply the same changes as Step 9, but for the test stack. The key differences in the test compose file are:
- All `./test_db/*` volumes instead of `./db/*`
- Different host ports (currently the test stack uses offset ports)

The `unified_api` service in `docker-compose-test.yaml`:

```yaml
  unified_api:
    build:
      context: .
      dockerfile: unified_api/Dockerfile.compose
    container_name: unified-api-test
    env_file:
      - .env
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: ${NEO4J_USERNAME:-neo4j}
      NEO4J_USERNAME: ${NEO4J_USERNAME:-neo4j}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      NEO4J_DATABASE: neo4j
      NEO4J_ENABLED: "true"
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DATABASE: ${POSTGRES_DB_RA_LITERAG:-ra_literag}
      CHROMA_HOST: chroma
      CHROMA_PORT: "8000"
      LIGHTRAG_VECTOR_STORAGE: ChromaVectorDBStorage
      LIGHTRAG_GRAPH_STORAGE: Neo4JStorage
      OLLAMA_API_BASE: http://ollama:11434
      OLLAMA_BASE_URL: http://ollama:11434
      LLM_SERVICE_BASE_URL: http://localhost:18000/llm-service
    volumes:
      - ./unified_api/logs:/app/logs
      - ./test_db/core_rag_graph/data:/repo/core_rag_graph/data
      - ./doc_processing/data/temp:/repo/doc_processing/data/temp
      - ./test_db/ra_literag_data:/repo/ra_literag/rag_storage
    ports:
      - "18000:8000"    # test stack host port 18000
    depends_on:
      neo4j:
        condition: service_healthy
      postgres:
        condition: service_healthy
      chroma:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 60s
    restart: unless-stopped
```

**Remove** `doc_processing`, `llm-service`, `core_rag_graph`, `ra_literag`, `temporial_graph`, `temporial_graph_openai`, `temporial_graph_traversal` from `docker-compose-test.yaml`.

---

## Step 11 — Merge environment variable files

### 11a — Create `unified_api/.env.example`

```dotenv
# ════════════════════════════════════════════════════════════════════════
# Unified API — environment variables reference
# Copy this file to /media/prashanth/extmnt1/common/.env and fill in values.
# ════════════════════════════════════════════════════════════════════════

# ── Required: database passwords ────────────────────────────────────────
NEO4J_PASSWORD=<set-a-strong-password>
POSTGRES_PASSWORD=<set-a-strong-password>

# ── Optional: database usernames / names (defaults shown) ───────────────
NEO4J_USERNAME=neo4j
POSTGRES_USER=postgres
POSTGRES_DB_RA_LITERAG=ra_literag
POSTGRES_DB_FIN_RAG=fin_rag
POSTGRES_BOOTSTRAP_DB=postgres

# ── LLM API keys (at least one required for LLM features) ───────────────
GROQ_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_PLAN=FREE

# ── Ollama model pulling (used by ollama_init service) ───────────────────
OLLAMA_PULL_MODELS=nomic-embed-text-v2-moe:latest,ibm/granite3.3-vision:2b,ibm/granite-docling:latest,glm-ocr:latest,deepseek-ocr:latest
OLLAMA_PULL_MODELS_EXTRA=

# ── core_rag_graph backend ───────────────────────────────────────────────
# Options: networkx (default, no DB) | neo4j
GRAPH_BACKEND=networkx
GRAPH_DUAL_WRITE=false

# ── temporial_graph_openai job queue ────────────────────────────────────
# Options: memory (default) | redis
JOB_BACKEND=memory
REDIS_URL=

# ── Debug ────────────────────────────────────────────────────────────────
DEBUG=false
LITELLM_DEBUG=false
LLM_STARTUP_MODELS_CHECK=false
```

### 11b — Update `.gitignore` at repo root

Add to `/media/prashanth/extmnt1/common/.gitignore`:

```gitignore
# unified_api
/unified_api/logs/*
!/unified_api/logs/.gitkeep
/unified_api/.env
/unified_api/.venv/
```

### 11c — Create data volume directories

```bash
mkdir -p /media/prashanth/extmnt1/common/db/core_rag_graph/data
mkdir -p /media/prashanth/extmnt1/common/db/ra_literag_data
mkdir -p /media/prashanth/extmnt1/common/test_db/core_rag_graph/data
mkdir -p /media/prashanth/extmnt1/common/test_db/ra_literag_data
touch /media/prashanth/extmnt1/common/db/core_rag_graph/data/.gitkeep
touch /media/prashanth/extmnt1/common/db/ra_literag_data/.gitkeep
touch /media/prashanth/extmnt1/common/test_db/core_rag_graph/data/.gitkeep
touch /media/prashanth/extmnt1/common/test_db/ra_literag_data/.gitkeep
```

---

## Step 12 — Validation checklist

Run these checks in order. Each must pass before proceeding to the next.

### 12.1 Dependency lock succeeds

```bash
cd /media/prashanth/extmnt1/common/unified_api
uv lock
# Expected: lock file written, no conflicts printed
```

### 12.2 Local import test (no Docker required)

```bash
cd /media/prashanth/extmnt1/common/unified_api
uv sync --dev
uv run python -c "from unified_api.main import app; print('OK', len(app.routes), 'routes')"
# Expected: OK <N> routes  (N should be > 30)
```

### 12.3 Local server starts

```bash
cd /media/prashanth/extmnt1/common/unified_api
# Requires databases to be running; use docker compose for DBs only
docker compose -f ../docker-compose.yml up -d postgres neo4j chroma ollama

uv run uvicorn unified_api.main:app --port 8000 --reload
# Expected: "Application startup complete" in logs, no import errors
```

### 12.4 Unified health endpoint

```bash
curl -fsS http://127.0.0.1:8000/health
# Expected: {"status":"ok","service":"unified-api"}
```

### 12.5 Per-service health endpoints

```bash
curl -fsS http://127.0.0.1:8000/llm-service/health
curl -fsS http://127.0.0.1:8000/doc-processing/health
curl -fsS http://127.0.0.1:8000/core-rag/health
curl -fsS http://127.0.0.1:8000/ra-literag/health
curl -fsS http://127.0.0.1:8000/temporal-graph/health
curl -fsS http://127.0.0.1:8000/temporal-graph-openai/health
curl -fsS http://127.0.0.1:8000/temporal-graph-traversal/health
# Expected: each returns {"status":"ok"} or similar
```

### 12.6 OpenAPI document completeness

```bash
curl -fsS http://127.0.0.1:8000/openapi.json | python3 -c "
import json, sys
doc = json.load(sys.stdin)
paths = list(doc['paths'].keys())
print(f'Total routes: {len(paths)}')
prefixes = ['/llm-service', '/doc-processing', '/core-rag', '/ra-literag',
            '/temporal-graph/', '/temporal-graph-openai', '/temporal-graph-traversal']
for p in prefixes:
    count = sum(1 for path in paths if path.startswith(p))
    print(f'  {p}: {count} routes')
"
```

Each prefix should have at least 2 routes.

### 12.7 Docker build (code)

```bash
cd /media/prashanth/extmnt1/common
docker compose --env-file .env build unified_api
# Expected: build completes without errors
```

### 12.8 Full Compose stack smoke test

```bash
cd /media/prashanth/extmnt1/common
docker compose --env-file .env up -d
docker compose --env-file .env ps
# Wait for unified_api to be healthy (may take 60s for startup)
docker compose --env-file .env logs unified_api --tail=50

curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/llm-service/health
```

### 12.9 Functional LLM test

```bash
curl -fsS -X POST http://127.0.0.1:8000/llm-service/llm/models
# Expected: list of available models
```

> **Note:** Step 13 (documentation) can be started in parallel with Steps 1–12 once the route prefix map (Section 4) is agreed. Finish Step 13 after Step 12 passes so examples and URLs match the running unified server.

---

## Step 13 — Unify documentation into `docs/`

### Why this step exists

Each service currently owns its own README, `docs/` folder, and OpenAPI export. After unification, operators and external integrators need **one place** to learn how to run the stack, configure env vars, and call APIs. Per-service READMEs that still reference separate host ports (`8020`, `8010`, `20050`, etc.) will be wrong.

This step creates a **canonical documentation tree** under `docs/` at the repo root. Per-service READMEs are **not deleted** — they receive a short banner pointing to the unified docs so standalone development still works.

### Goals

1. Single entry point: `docs/README.md` (documentation index).
2. Unified operational runbook (Compose, env, Ollama, logs) — evolved from repo-root `README.md`.
3. Per-service guides under `docs/services/<name>/` with updated base URLs and route prefixes.
4. Consolidated API reference section with links to OpenAPI JSON and human-readable endpoint guides.
5. Cross-links between related docs (e.g. `doc_processing` chunking ↔ `llm-service` embeddings).

### Principles for Cursor agents and humans

| Principle | Rule |
|-----------|------|
| **Canonical location** | After this step, `docs/` is the source of truth for unified operation. |
| **Do not delete service READMEs** | Add a 3-line banner at the top linking to `docs/services/<name>/`. |
| **Update URLs and ports** | Replace old per-service host ports with unified prefix paths (Section 4). |
| **Preserve technical depth** | Move or copy substantive guides; do not summarise away operational detail. |
| **Mark historical docs** | Split/migration plans (e.g. `SERVICE_SPLIT_PLAN.md`) go under `docs/archive/` with a note that they describe the pre-unification layout. |
| **OpenAPI** | Keep machine-readable specs; add a note that live spec is `GET /openapi.json` on the unified server. |
| **fin_rag** | Out of unified API scope; include an appendix entry only (still a separate Compose service). |

### Target `docs/` layout

Create this structure (files marked `(new)` are written in this step; others may be copied or adapted from service trees):

```
docs/
├── README.md                              (new) Master documentation index
├── unified-api-implementation-plan.md     (existing) This plan
├── compose-runbook.md                     (new) Docker Compose ops — from repo README.md
├── unified-api/
│   ├── README.md                          (new) Running the unified server (local + Docker)
│   ├── configuration.md                   (new) All env vars; links to unified_api/.env.example
│   ├── api-overview.md                    (new) Route prefixes, health checks, Swagger /docs
│   └── migration-notes.md                 (new) Old port → new prefix table for integrators
├── services/
│   ├── llm-service/
│   │   ├── README.md                      ← llm-service/README.md (updated)
│   │   └── openapi.md                     (new) How to regenerate + prefix note
│   ├── doc-processing/
│   │   ├── README.md                      ← doc_processing/README.md (updated)
│   │   ├── document-chunking.md           ← doc_processing/docs/DOCUMENT_CHUNKING.md
│   │   └── references.md                ← doc_processing/docs/REFERENCES.md
│   ├── core-rag-graph/
│   │   ├── README.md                      ← core_rag_graph/README.md (updated)
│   │   ├── neo4j-cutover-checklist.md     ← core_rag_graph/docs/cutover-checklist.md
│   │   ├── neo4j-migration-runbook.md     ← core_rag_graph/docs/runbook-migration-cutover.md
│   │   └── openapi.md                     (new) Points to docs/openapi/core-rag-graph.json
│   ├── ra-literag/
│   │   ├── README.md                      (new) Service-focused; not full upstream RAG-Anything README
│   │   ├── service.md                     ← ra_literag/docs/service.md
│   │   ├── config-reference.md            ← ra_literag/app/config_reference.md
│   │   ├── offline-setup.md               ← ra_literag/docs/offline_setup.md
│   │   ├── batch-processing.md            ← ra_literag/docs/batch_processing.md
│   │   └── openapi.md                     ← ra_literag/docs/openapi.md (update paths)
│   ├── temporal-graph/
│   │   ├── README.md                      ← temporial_graph/docs/README.md (index, updated)
│   │   ├── design.md                      ← temporial_graph/docs/DESIGN.md
│   │   ├── developer-guide.md             ← temporial_graph/docs/DEVELOPER_ENHANCEMENTS.md
│   │   ├── openapi.md                     ← temporial_graph/docs/OPENAPI.md (update paths)
│   │   ├── ontology.md                    ← temporial_graph/docs/ONTOLOGY.md
│   │   └── multi-project-spec.md          ← temporial_graph/docs/MULTI_PROJECT_OPERATING_SPEC.md
│   ├── temporal-graph-openai/
│   │   ├── README.md                      ← temporial_graph_openai/docs/README.md (updated)
│   │   ├── developer.md                   ← temporial_graph_openai/docs/DEVELOPER.md
│   │   ├── ontologies.md                  ← temporial_graph_openai/docs/ONTOLOGIES.md
│   │   ├── openapi.md                     ← temporial_graph_openai/docs/openapi.md (update paths)
│   │   ├── canonical-events.md            ← temporial_graph_openai/canonical_events.md
│   │   └── financial-entity-schema.md     ← temporial_graph_openai/financial_entity_schema.md
│   └── temporal-graph-traversal/
│       ├── README.md                      (new) RAQE overview + quickstart
│       ├── reference-query-engine.md      ← temporial_graph_traversal/docs/reference_query_engine_final.md
│       ├── implementation-plan.md         ← temporial_graph_traversal/docs/raqe_phasewise_implementation_plan.md
│       └── phase-guides/                  ← phase1–phase9 comprehensive docs (as needed)
├── openapi/                               (new) Frozen per-service OpenAPI exports (optional snapshots)
│   ├── README.md                          (new) How specs relate to live /openapi.json
│   ├── llm-service.json
│   ├── doc-processing.json
│   ├── core-rag-graph.json
│   ├── ra-literag.json
│   ├── temporal-graph.json
│   └── temporal-graph-openai.json
└── archive/                               (new) Historical / superseded docs
    ├── doc-processing-service-split.md    ← doc_processing/docs/SERVICE_SPLIT_PLAN.md
    └── doc-processing-pr-split.md           ← doc_processing/docs/PR_PLAN_SERVICE_SPLIT.md
```

### Source inventory (what to pull from each service)

Use this table when copying or adapting content. Paths are relative to repo root.

| Service | Source file(s) | Target under `docs/` | Action |
|---------|----------------|----------------------|--------|
| **Repo root** | `README.md` | `docs/compose-runbook.md` | Extract Compose/Ollama/logs sections; add unified_api service; link to `docs/unified-api/` |
| **llm-service** | `llm-service/README.md` | `docs/services/llm-service/README.md` | Copy + update run instructions for unified prefix `/llm-service` |
| **llm-service** | `llm-service/openapi.json`, `openapi.snapshot.json` | `docs/openapi/llm-service.json` | Copy snapshot; document regeneration command with prefix note |
| **doc_processing** | `doc_processing/README.md` | `docs/services/doc-processing/README.md` | Copy + update; note `LLM_SERVICE_BASE_URL` points at unified `/llm-service` |
| **doc_processing** | `doc_processing/docs/DOCUMENT_CHUNKING.md` | `docs/services/doc-processing/document-chunking.md` | Copy as-is; fix internal links if any |
| **doc_processing** | `doc_processing/docs/REFERENCES.md` | `docs/services/doc-processing/references.md` | Copy as-is |
| **doc_processing** | `doc_processing/docs/SERVICE_SPLIT_PLAN.md`, `PR_PLAN_SERVICE_SPLIT.md` | `docs/archive/` | Move with “historical” header |
| **doc_processing** | `doc_processing/openapi.json` | `docs/openapi/doc-processing.json` | Copy |
| **core_rag_graph** | `core_rag_graph/README.md` | `docs/services/core-rag-graph/README.md` | Copy + update Neo4j/LLM URLs |
| **core_rag_graph** | `core_rag_graph/docs/*.md` | `docs/services/core-rag-graph/` | Copy operational docs (cutover, rollback, neo4j plan) |
| **core_rag_graph** | `core_rag_graph/docs/openapi.json` | `docs/openapi/core-rag-graph.json` | Copy |
| **ra_literag** | `ra_literag/docs/service.md` | `docs/services/ra-literag/service.md` | Copy + update workspace/API examples |
| **ra_literag** | `ra_literag/app/config_reference.md` | `docs/services/ra-literag/config-reference.md` | Copy |
| **ra_literag** | `ra_literag/docs/*.md` (except openapi) | `docs/services/ra-literag/` | Copy relevant guides |
| **ra_literag** | `ra_literag/README.md` | — | **Do not copy wholesale** (upstream RAG-Anything marketing README). Write a short service README linking to `service.md` |
| **ra_literag** | `ra_literag/README_zh.md` | — | Leave in place; optional link from index |
| **temporial_graph** | `temporial_graph/docs/README.md` + linked docs | `docs/services/temporal-graph/` | Copy index + DESIGN, DEVELOPER_ENHANCEMENTS, OPENAPI, ONTOLOGY, MULTI_PROJECT |
| **temporial_graph** | `temporial_graph/docs/openapi.json` | `docs/openapi/temporal-graph.json` | Copy |
| **temporial_graph_openai** | `temporial_graph_openai/docs/*` | `docs/services/temporal-graph-openai/` | Copy developer, ontologies, openapi guides |
| **temporial_graph_openai** | `canonical_events.md`, `financial_entity_schema.md` | `docs/services/temporal-graph-openai/` | Copy |
| **temporial_graph_openai** | `temporial_graph_openai/openapi.json` | `docs/openapi/temporal-graph-openai.json` | Copy |
| **temporial_graph_traversal** | `temporial_graph_traversal/docs/reference_query_engine_final.md` | `docs/services/temporal-graph-traversal/` | Copy primary reference |
| **temporial_graph_traversal** | `temporial_graph_traversal/docs/phase*_*.md`, `raqe_*.md` | `docs/services/temporal-graph-traversal/phase-guides/` | Copy or index; link from README |
| **fin_rag** (appendix) | `fin_rag/README.md` | `docs/services/fin-rag/README.md` | Optional: short note that fin_rag remains separate on port 6005 |

### Sub-step 13.1 — Create `docs/README.md` (master index)

**File:** `docs/README.md`

This is the **first document** new users and agents should open. Include:

1. One-paragraph description of the unified API and what lives in this repo.
2. Link to [unified-api-implementation-plan.md](./unified-api-implementation-plan.md) (implementation status).
3. **Quick start** (3 commands): `cp .env.example .env`, `docker compose up -d`, `curl http://127.0.0.1:8000/health`.
4. **Documentation map** table:

| Document | Audience | Description |
|----------|----------|-------------|
| [compose-runbook.md](./compose-runbook.md) | Operators | Docker Compose, test stack, Ollama, logs |
| [unified-api/README.md](./unified-api/README.md) | Developers | Run unified server locally |
| [unified-api/configuration.md](./unified-api/configuration.md) | Operators | Environment variables |
| [unified-api/api-overview.md](./unified-api/api-overview.md) | Integrators | Route prefixes and health endpoints |
| [unified-api/migration-notes.md](./unified-api/migration-notes.md) | Integrators | Old microservice URLs → unified paths |
| [services/](./services/) | Per-feature | Deep dives per merged service |
| [openapi/](./openapi/) | Integrators | Frozen OpenAPI snapshots |

5. Link to live Swagger UI: `http://<host>:8000/docs` (when unified server is running).

### Sub-step 13.2 — Create `docs/compose-runbook.md`

**Source:** Repo-root `README.md` (Common Services Compose Runbook).

**Actions:**

1. Copy the operational content from `README.md` (prerequisites, env, build cache, smoke test, Ollama, logs, test vs live compose).
2. **Replace** the seven per-service `docker compose up <service>` examples with `unified_api` where appropriate.
3. Update the service/port table to show:
   - **Unified API:** host `8000` → all seven feature areas under path prefixes.
   - **Infrastructure:** postgres `5432`, neo4j `7474`/`7687`, chroma `8001`, ollama `11434`.
   - **fin_rag:** still `6005` (separate service).
4. Keep `docker-compose-test.yaml` differences (host port `18000` for unified API in test stack).
5. Add a “Documentation” section linking back to `docs/README.md`.

**Then edit repo-root `README.md`** to a **short pointer** (≤ 30 lines):

```markdown
# Common Services

Unified FastAPI stack and Docker Compose for RAG, document processing, and temporal graph services.

**Documentation:** [docs/README.md](docs/README.md)

Quick start:

```bash
cp .env.example .env
# edit NEO4J_PASSWORD, POSTGRES_PASSWORD
docker compose --env-file .env up -d unified_api
curl http://127.0.0.1:8000/health
```
```

### Sub-step 13.3 — Create `docs/unified-api/` guides

#### `docs/unified-api/README.md`

- How to run with Docker (`docker compose up unified_api`).
- How to run locally (`cd unified_api && uv sync && uv run uvicorn unified_api.main:app --port 8000`).
- Dependency on infra services (postgres, neo4j, chroma, ollama).
- Link to implementation plan for architecture detail.

#### `docs/unified-api/configuration.md`

- Merge content from `unified_api/.env.example` (Step 11) into prose.
- Group vars: shared (Neo4j, Postgres, Chroma, Ollama), per-service optional blocks.
- Document `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` for in-container unified mode.
- Note `NEO4J_USER` vs `NEO4J_USERNAME` (both set in Compose for compatibility).

#### `docs/unified-api/api-overview.md`

- Table of all prefixes and primary endpoints (from Section 4 of this plan).
- Health check curl examples (same as Step 12.5).
- Explain unified `GET /openapi.json` vs frozen files in `docs/openapi/`.
- List middleware that affects paths (collection ID middleware on core-rag and temporal-graph services).

#### `docs/unified-api/migration-notes.md`

**Audience:** External systems that previously called separate host ports.

| Old base URL (live stack) | New base URL |
|---------------------------|--------------|
| `http://host:8020` (llm-service) | `http://host:8000/llm-service` |
| `http://host:8010` (doc_processing) | `http://host:8000/doc-processing` |
| `http://host:20050` (core_rag_graph) | `http://host:8000/core-rag` |
| `http://host:8000` (ra_literag) | `http://host:8000/ra-literag` |
| `http://host:8082` (temporial_graph) | `http://host:8000/temporal-graph` |
| `http://host:8080` (temporial_graph_openai) | `http://host:8000/temporal-graph-openai` |
| `http://host:8090` (temporial_graph_traversal) | `http://host:8000/temporal-graph-traversal` |

Include test-stack host port `18000` variant for `docker-compose-test.yaml`.

State explicitly: **request and response JSON schemas are unchanged**; only the URL prefix changes.

### Sub-step 13.4 — Populate `docs/services/<name>/`

For **each** of the seven services:

1. Create the target directory under `docs/services/`.
2. Copy or adapt files per the source inventory table above.
3. At the top of each service `README.md`, add:

```markdown
> **Unified API:** This service is mounted at `/<prefix>` on the unified server (default `http://127.0.0.1:8000`). See [API overview](../../unified-api/api-overview.md) and [migration notes](../../unified-api/migration-notes.md).
```

4. **Search-and-replace** in copied docs (per file):
   - Old localhost ports → unified paths (use migration table).
   - `http://llm-service:8001` → `http://localhost:8000/llm-service` (in-container) or document both Docker internal and host access patterns.
   - `curl http://localhost:8082/...` → `curl http://localhost:8000/temporal-graph/...` (adjust per service).
5. Fix relative links between moved docs (e.g. `./DESIGN.md` → `./design.md` if filenames were normalized to kebab-case).

**Naming convention:** Prefer `kebab-case.md` filenames in `docs/` for consistency. When copying, rename unless a well-known name (e.g. `openapi.md`) should stay.

### Sub-step 13.5 — Consolidate OpenAPI under `docs/openapi/`

**File:** `docs/openapi/README.md`

Explain:

1. **Live spec:** `GET http://<host>:8000/openapi.json` includes all mounted routers (may be large).
2. **Frozen per-service snapshots** in this directory are for contract review and CI; paths in frozen files reflect **pre-unification** paths unless regenerated with prefixes.
3. How to regenerate after unified server is running:

```bash
# Full unified spec
curl -fsS http://127.0.0.1:8000/openapi.json -o docs/openapi/unified.json

# Per-service (filter by prefix) — optional script
python3 scripts/export_unified_openapi_by_prefix.py  # create if useful
```

4. Link to existing per-service export commands where they still work standalone (e.g. `llm-service` export one-liner from its README).

**Copy** these files into `docs/openapi/` (refresh from source if newer):

- `llm-service/openapi.json` → `llm-service.json`
- `doc_processing/openapi.json` → `doc-processing.json`
- `core_rag_graph/docs/openapi.json` → `core-rag-graph.json`
- `ra_literag/docs/openapi.json` → `ra-literag.json`
- `temporial_graph/docs/openapi.json` → `temporal-graph.json`
- `temporial_graph_openai/openapi.json` → `temporal-graph-openai.json`

`temporial_graph_traversal` has no committed OpenAPI file — note in README that spec comes from live `/openapi.json` or add export in a follow-up.

### Sub-step 13.6 — Add deprecation banners to per-service READMEs

At the **top** of each service's repo-root `README.md` (do not remove existing content below):

```markdown
> **Documentation has moved.** For unified Docker Compose and API usage, see [docs/README.md](../docs/README.md) and [docs/services/<service-name>/](../docs/services/<service-name>/). This file remains for standalone development of this package only.
```

Apply to:

- `llm-service/README.md`
- `doc_processing/README.md`
- `core_rag_graph/README.md`
- `ra_literag/README.md` (below any upstream badges, or replace intro with pointer if too long)
- `temporial_graph/docs/README.md` → also add pointer to `docs/services/temporal-graph/`
- `temporial_graph_openai/docs/README.md`
- Create `temporial_graph_traversal/README.md` if missing, with pointer + link to `docs/services/temporal-graph-traversal/`

### Sub-step 13.7 — Update Cursor agent context (optional but recommended)

If the repo uses `.cursor/skills/` or rules that reference per-service ports:

1. Read `.cursor/skills/docker-compose-unified/SKILL.md` and update service list to `unified_api` + infra + `fin_rag`.
2. Add a one-line reference in that skill: “Full documentation: `docs/README.md`”.
3. Do **not** duplicate the entire implementation plan inside the skill — link to `docs/unified-api-implementation-plan.md`.

### Sub-step 13.8 — Documentation validation checklist

Run after all doc files are in place:

```bash
cd /media/prashanth/extmnt1/common

# 1. Master index exists
test -f docs/README.md && echo OK docs/README.md

# 2. All seven service doc dirs exist
for s in llm-service doc-processing core-rag-graph ra-literag temporal-graph temporal-graph-openai temporal-graph-traversal; do
  test -d "docs/services/$s" && echo OK "docs/services/$s" || echo MISSING "docs/services/$s"
done

# 3. No stale port references in docs/ (manual review — flag common old ports)
rg -n ':(8020|8010|20050|8082|8080|8090)\b' docs/ || echo "No old host ports found (good)"

# 4. Migration doc lists all seven prefixes
rg -n '/llm-service|/doc-processing|/core-rag|/ra-literag|/temporal-graph' docs/unified-api/migration-notes.md

# 5. Repo README points to docs/
rg -n 'docs/README.md' README.md

# 6. OpenAPI snapshots present
ls docs/openapi/*.json | wc -l   # expect >= 6
```

**Manual review checklist:**

- [ ] Every `curl` example in `docs/` uses unified base URL or documents both modes.
- [ ] `docs/compose-runbook.md` matches `docker-compose.yml` after Step 9.
- [ ] `docs/unified-api/configuration.md` matches `unified_api/settings.py` field list.
- [ ] Cross-links between docs resolve (no broken relative paths).
- [ ] `ra_literag` service README is service-scoped, not a duplicate of the 1300-line upstream README.

### Step 13 completion criteria

Step 13 is **done** when:

1. `docs/README.md` exists and links to all major sections.
2. All seven services have a directory under `docs/services/`.
3. Repo-root `README.md` is a short pointer to `docs/`.
4. `docs/unified-api/migration-notes.md` documents old port → new prefix mapping.
5. `docs/openapi/` contains frozen JSON for at least six services.
6. Per-service READMEs include the deprecation/pointer banner.
7. Documentation validation checklist (13.8) passes with no `MISSING` dirs.

---

## Phase 2 — Optimise internal LLM calls (optional)

After Phase 1 is stable, the HTTP round-trip from services to `llm-service` can be replaced with direct Python function calls. This eliminates network overhead for internal completions and embeddings.

**Services affected:**

| Service | Current call | Call location |
|---------|-------------|---------------|
| `doc_processing` | `POST http://llm-service:8001/llm/complete` | `doc_processing/src/doc_processing/llm_runtime/` |
| `core_rag_graph` | `POST $LLM_SERVICE_BASE_URL/llm/complete` | `core_rag_graph/utils/call_llm_api.py` |
| `ra_literag` | `LLM_SERVICE_BASE_URL` via `DocProcessingLLMClient` | `ra_literag/app/llm_client.py` |
| `temporial_graph` | `LLM_SERVICE_BASE_URL` via `LLMClient` | `temporial_graph/src/temporial_graph_rag/llm/client.py` |
| `temporial_graph_openai` | `LLM_SERVICE_BASE_URL` via `DocProcessingClient` | `temporial_graph_openai/temporal_graph/llm/client.py` |
| `temporial_graph_traversal` | `LLM_SERVICE_BASE_URL/llm/complete` (optional) | `temporial_graph_traversal/app/llm/client.py` |

**Implementation pattern for each service:**

1. Identify the HTTP client class.
2. Import the `llm_service` handler function directly:
   ```python
   from llm_service.routers.llm import complete  # the route handler function
   ```
3. Create an `InProcessLLMClient` that calls the handler directly, bypassing HTTP.
4. Add an env var `LLM_CLIENT_MODE=http|inprocess` (default `inprocess` when `LLM_SERVICE_BASE_URL` starts with `http://localhost`).
5. Factory function selects which client to instantiate.

**This step is fully optional.** Setting `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` in the unified compose service is a valid and functional approach for Phase 1.

---

## What Does NOT Change

| Item | Status |
|------|--------|
| Route handler logic in any service | **Unchanged** |
| Pydantic request/response model schemas | **Unchanged** |
| Database table schemas (Postgres, Neo4j, Chroma) | **Unchanged** |
| Per-service `pyproject.toml` files | **Unchanged** (except `temporial_graph_traversal` in Step 1) |
| Per-service `Dockerfile.compose` files | **Unchanged** (services still buildable/runnable standalone) |
| `fin_rag` and `fin_rag_migrate` | **Unchanged** |
| Ollama `pull-models.sh` script | **Unchanged** |
| `.env.example` files per service | **Unchanged** (kept as reference) |
| Per-service `README.md` bodies | **Unchanged** (banner added at top in Step 13; standalone dev still documented) |
| Per-service `docs/` folders | **Unchanged** (canonical copy lives under repo `docs/`; service copies may stay as mirrors) |

---

## Complete File Change Summary

### New files to create

| File | Created in step |
|------|----------------|
| `unified_api/__init__.py` | Step 3 |
| `unified_api/main.py` | Step 3 (placeholder) → Step 7 (final) |
| `unified_api/lifespan.py` | Step 3 (placeholder) → Step 6 (final) |
| `unified_api/settings.py` | Step 3 (placeholder) → Step 5 (final) |
| `unified_api/pyproject.toml` | Step 4 |
| `unified_api/uv.lock` | Step 4 (generated by `uv lock`) |
| `unified_api/Dockerfile.compose` | Step 8 |
| `unified_api/.dockerignore` | Step 8 |
| `unified_api/logs/.gitkeep` | Step 3 |
| `unified_api/.env.example` | Step 11 |
| `core_rag_graph/routers/__init__.py` | Step 2a |
| `core_rag_graph/routers/health.py` | Step 2a |
| `core_rag_graph/routers/graph_api.py` | Step 2a |
| `core_rag_graph/state.py` | Step 2a |
| `ra_literag/app/routers/__init__.py` | Step 2b |
| `ra_literag/app/routers/health.py` | Step 2b |
| `ra_literag/app/routers/config.py` | Step 2b |
| `ra_literag/app/routers/query.py` | Step 2b |
| `ra_literag/app/routers/ingest.py` | Step 2b |
| `ra_literag/app/rag_cache.py` | Step 2b |
| `temporial_graph/src/temporial_graph_rag/api/routers/__init__.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/routers/health.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/routers/collections.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/routers/search.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/routers/ingest.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/routers/network.py` | Step 2c |
| `temporial_graph/src/temporial_graph_rag/api/dependencies.py` | Step 2c |
| `temporial_graph_openai/temporal_graph/api/health_routes.py` | Step 2d |
| `temporial_graph_traversal/app/api/health_routes.py` | Step 2e |
| `temporial_graph_traversal/app/__init__.py` | Step 1 |
| `db/core_rag_graph/data/.gitkeep` | Step 11 |
| `db/ra_literag_data/.gitkeep` | Step 11 |
| `test_db/core_rag_graph/data/.gitkeep` | Step 11 |
| `test_db/ra_literag_data/.gitkeep` | Step 11 |
| `docs/README.md` | Step 13 |
| `docs/compose-runbook.md` | Step 13 |
| `docs/unified-api/README.md` | Step 13 |
| `docs/unified-api/configuration.md` | Step 13 |
| `docs/unified-api/api-overview.md` | Step 13 |
| `docs/unified-api/migration-notes.md` | Step 13 |
| `docs/openapi/README.md` | Step 13 |
| `docs/openapi/*.json` (6+ snapshots) | Step 13 |
| `docs/services/<service>/*` (per inventory) | Step 13 |
| `docs/archive/*` (historical split plans) | Step 13 |

### Files to edit

| File | Edited in step |
|------|---------------|
| `temporial_graph_traversal/pyproject.toml` | Step 1 (enable packaging) |
| `core_rag_graph/graph_server.py` | Step 2a (router includes, lifespan migration) |
| `ra_literag/app/main.py` | Step 2b (router includes, remove inline routes) |
| `temporial_graph/src/temporial_graph_rag/api/main.py` | Step 2c (router includes, remove inline routes) |
| `temporial_graph_openai/temporal_graph/api/main.py` | Step 2d (remove inline /health) |
| `temporial_graph_traversal/app/main.py` | Step 2e (remove inline /health) |
| `docker-compose.yml` | Step 9 (remove 7 services, add unified_api) |
| `docker-compose-test.yaml` | Step 10 (remove 7 services, add unified_api) |
| `.gitignore` | Step 11 |
| `README.md` (repo root) | Step 13 (short pointer to docs/) |
| `llm-service/README.md` | Step 13 (deprecation banner) |
| `doc_processing/README.md` | Step 13 (deprecation banner) |
| `core_rag_graph/README.md` | Step 13 (deprecation banner) |
| `ra_literag/README.md` | Step 13 (deprecation banner) |
| `temporial_graph/docs/README.md` | Step 13 (pointer to docs/services/temporal-graph/) |
| `temporial_graph_openai/docs/README.md` | Step 13 (pointer) |
| `.cursor/skills/docker-compose-unified/SKILL.md` | Step 13 (optional: unified_api service list) |

---

## Rollback Procedure

If the unified server does not work and you need to revert to the individual services:

1. **Revert `docker-compose.yml`:**
   ```bash
   git checkout docker-compose.yml
   ```

2. **Revert `docker-compose-test.yaml`:**
   ```bash
   git checkout docker-compose-test.yaml
   ```

3. The individual services' `Dockerfile.compose` files and source code were not changed (except for the router refactor in Step 2 and packaging change in Step 1). If step 2 changes caused regressions in standalone operation, revert those files:
   ```bash
   git checkout core_rag_graph/graph_server.py
   git checkout ra_literag/app/main.py
   git checkout temporial_graph/src/temporial_graph_rag/api/main.py
   git checkout temporial_graph_traversal/pyproject.toml
   ```

4. Restart individual services:
   ```bash
   docker compose --env-file .env up -d
   ```

The `unified_api/` directory can remain on disk without affecting anything — it is not referenced by `docker-compose.yml` after rollback.

5. **Documentation (Step 13):** Unified docs under `docs/` do not affect runtime. To revert doc changes only:
   ```bash
   git checkout README.md
   git checkout docs/
   git checkout */README.md
   ```
   Or keep unified docs and restore only repo-root `README.md` if you need the old compose runbook inline.

---

## Recommended implementation order

1. **Step 2** (pyproject.toml + `uv lock`) — validates dependency compatibility first; fail fast if there are conflicts
2. **Step 1** (skeleton) — minimal app that starts
3. **Step 3** (router refactors) — most complex; verify per-service standalone behaviour after each
4. **Step 4 + 5** (settings + lifespan) — wire databases
5. **Step 6** (mount routers) — full wiring
6. **Step 7** (Dockerfile) — containerize
7. **Step 8–10** (compose update) — integrate into stack
8. **Step 11** (env files) — operator reference
9. **Step 12** (validation) — prove the unified server works
10. **Step 13** (documentation) — unify READMEs and guides under `docs/`; can start drafting migration-notes and folder layout in parallel with Steps 8–11
11. **Phase 2** (internal LLM calls) — optional optimization

---

*End of implementation plan. All steps are ordered for minimal risk. Complete and verify each step before proceeding to the next.*
