# ra-literag FastAPI service

**ra-literag** is the HTTP wrapper around in-repo **RAGAnything** (LightRAG + multimodal parsing). It exposes query, ingest, and config APIs. All LLM completions and embeddings go through an external **doc-processing** service, not direct provider SDKs from this app.

---

## Prerequisites

- **Python** ≥ 3.10, **[uv](https://github.com/astral-sh/uv)** for installs and runs.
- **llm-service** reachable at `LLM_SERVICE_BASE_URL` (default `http://localhost:8081`). It must implement the LLM proxy API (`/llm/complete`, `/llm/embeddings`, `/llm/models`). Reference schema: [`docs/doc_processing_openapi.json`](doc_processing_openapi.json).
- **LightRAG storage** you configure via env (e.g. Chroma, Neo4j, JSON paths). Defaults in `app/config.py` assume Chroma + Neo4j + JSON-style storages; adjust `LIGHTRAG_*_STORAGE` and connection env vars to match your deployment.
- Optional **PostgreSQL** for per-workspace overrides: if `POSTGRES_DATABASE` is set, the app creates `ra_litelag_config` and serves `GET`/`POST /config/{workspace_id}`.

Copy and edit environment from `env.example` (or your `.env`).

---

## Install

From the repository root:

```bash
uv sync
```

Optional document-format dependencies (Pillow, WeasyPrint, etc.):

```bash
uv sync --extra formats
```

Optional test tools:

```bash
uv sync --group dev
```

---

## Starting the server

**Console script** (uses `HOST` / `PORT`, enables **reload** for development):

```bash
uv run ra-literag
```

**Uvicorn directly** (typical for production; no reload unless you add `--reload`):

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOST` | `0.0.0.0` | Bind address (`ra-literag` entrypoint only) |
| `PORT` | `8000` | Listen port (`ra-literag` entrypoint only) |

`app.config` loads `.env` on import (`python-dotenv`). Set at least `LLM_SERVICE_BASE_URL` before queries will work; `/ready` returns 503 if it is unset.

---

## Usage model

- **Multi-tenant:** Pass **`workspace`** on each request (or rely on `WORKSPACE` / `WORKSPACE_DEFAULT` in env). LightRAG isolates data by workspace.
- **Per-workspace DB config:** With Postgres configured, `POST /config/{workspace_id}` stores JSON merged with env defaults; the next use of that workspace rebuilds the cached RAG instance.

Interactive API docs when the server is running:

- **Swagger UI:** `GET /docs`
- **ReDoc:** `GET /redoc`
- **OpenAPI JSON:** `GET /openapi.json`

Static copies for clients and CI live in this folder as [`openapi.json`](openapi.json) and [`openapi.yaml`](openapi.yaml). Regenerate after changing routes:

```bash
uv run python scripts/generate_openapi.py
```

See also [`openapi.md`](openapi.md).

---

## HTTP API summary

All JSON bodies use the models defined in `app/main.py` unless noted.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness; always `200` with body `ok`. |
| `GET` | `/ready` | Readiness; `503` if `LLM_SERVICE_BASE_URL` is not set. |

### Config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config` | Non-secret app snapshot: working dir, default workspace, parser, storage types, doc-processing base URL and LLM provider name. |
| `GET` | `/config/{workspace_id}` | Workspace overrides from Postgres. `404` if none. |
| `POST` | `/config/{workspace_id}` | Partial workspace config (validated; unknown keys rejected). `503` if Postgres is not configured. |

Allowed keys for `POST` mirror `WorkspaceConfigPayload` in `app/workspace_config.py` (e.g. `working_dir`, `parser`, `parse_method`, LightRAG storage fields, `top_k`, `vector_db_storage_cls_kwargs`, …).

### Query

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query` | Text RAG query: `workspace`, `query`, `mode` (`local`, `global`, `hybrid`, `naive`, `mix`, `bypass`), optional `vlm_enhanced`, `system_prompt`. Returns `{ "answer": "..." }`. |
| `POST` | `/query/multimodal` | Same idea with inline multimodal items (tables, equations, image paths). |

### Ingest

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/content/insert` | Insert a pre-parsed `content_list` (no file upload). |
| `POST` | `/documents/process` | `multipart/form-data`: file upload plus form fields `workspace`, optional `output_dir`, `parse_method`, `parser`, `doc_id`. Runs full parse + index for that workspace. |

---

## PostgreSQL (optional)

Set `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and **`POSTGRES_DATABASE`** for the pool to start and for workspace config endpoints to work. Table: **`ra_litelag_config`**.

---

## Related documentation

- **Doc-processing API (external):** [`doc_processing_openapi.json`](doc_processing_openapi.json)
- **This service OpenAPI:** [`openapi.md`](openapi.md)
- **RAGAnything / offline / integrations:** other files under `docs/` and the root `README.md`
