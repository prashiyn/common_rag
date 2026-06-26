# Unified API configuration

Environment variables are loaded from the repo-root `.env` (via Docker Compose `env_file`) and from per-service `.env` files where compose references them (`llm-service/.env`, `doc_processing/.env`).

Each merged service still reads configuration through its own settings module at runtime. This document is the operator reference.

## Required secrets

| Variable | Used by |
|----------|---------|
| `NEO4J_PASSWORD` | Neo4j auth; all graph services |
| `POSTGRES_PASSWORD` | Postgres auth; `ra_literag`, `fin_rag` |

`NEO4J_PASSWORD` must **not** be the default `neo4j`.

## Shared infrastructure

| Variable | Default (compose) | Purpose |
|----------|-------------------|---------|
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j bolt URL |
| `NEO4J_USER` | `neo4j` | Used by `core_rag_graph` |
| `NEO4J_USERNAME` | `neo4j` | Used by other graph services |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database name |
| `NEO4J_ENABLED` | `true` | `temporial_graph` Neo4j toggle |
| `POSTGRES_HOST` | `postgres` | Postgres hostname |
| `POSTGRES_PORT` | `5432` | Postgres port |
| `POSTGRES_USER` | `postgres` | Postgres user |
| `POSTGRES_DATABASE` | `ra_literag` | DB for `ra_literag` workspace config |
| `CHROMA_HOST` | `chroma` | Chroma hostname |
| `CHROMA_PORT` | `8000` | Chroma internal port |
| `OLLAMA_API_BASE` | `http://ollama:11434` | `llm-service` → Ollama |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | `doc_processing` Docling VLM |

## Unified server / inter-service

| Variable | Unified compose value | Purpose |
|----------|----------------------|---------|
| `LLM_SERVICE_BASE_URL` | `http://localhost:8000/llm-service` | In-container self-reference to LLM routes |
| `LLM_CLIENT_MODE` | `inprocess` (unified stack) | `inprocess` calls `llm_service` handlers directly; `http` uses REST |

When `LLM_CLIENT_MODE` is unset, services auto-select `inprocess` if `LLM_SERVICE_BASE_URL` starts with `http://localhost` or `http://127.0.0.1`. External callers (e.g. `fin_rag` at `http://unified_api:8000/llm-service`) always use HTTP.

Inside Docker, `localhost:8000` refers to the same `unified_api` container. External clients use the host-mapped port (`8000` live, `18000` test).

## LLM provider keys (`llm-service`)

Set in `llm-service/.env` or repo `.env`:

- `GROQ_API_KEY`, `GROQ_PLAN`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- `LITELLM_DEBUG`, `DEBUG`

## Ollama models

In repo-root `.env`:

```bash
OLLAMA_PULL_MODELS=nomic-embed-text-v2-moe:latest,ibm/granite3.3-vision:2b,ibm/granite-docling:latest,glm-ocr:latest,deepseek-ocr:latest
OLLAMA_PULL_MODELS_EXTRA=   # optional one-off pulls
```

See [compose-runbook.md](../compose-runbook.md#ollama-first-time-setup-required-once-per-stack).

## Per-service optional blocks

| Service | Key variables |
|---------|---------------|
| `core_rag_graph` | `GRAPH_BACKEND`, `GRAPH_DUAL_WRITE`, `LLM_CONFIG_PATH` |
| `ra_literag` | `LIGHTRAG_*_STORAGE`, `WORKSPACE`, `WORKING_DIR` |
| `temporial_graph` | `LLM_STARTUP_MODELS_CHECK`, `REDIS_URL` |
| `temporial_graph_openai` | `JOB_BACKEND`, `REDIS_URL`, `INGEST_MAX_CONCURRENT_JOBS` |
| `temporial_graph_traversal` | `COLLECTION_ALIASES`, `APP_PORT` |

## Example template

See `unified_api/.env.example` and repo-root `.env.example`.
