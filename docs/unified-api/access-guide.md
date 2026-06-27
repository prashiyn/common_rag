# Accessing the unified API

How to reach the unified API from your machine, from other Docker containers, and from external compose stacks.

**Default host port:** **18000** (`docker-compose-test.yaml`). Gateway: **18080**. Live stack uses **8000** / **8080** when those ports are free on the host.

## Prerequisites

1. Copy root env template and set secrets:

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD and NEO4J_PASSWORD (≥ 8 characters, non-default)
```

2. Start infrastructure and the API (see [Starting the service](#starting-the-service)).

---

## Base URLs at a glance

| Who is calling | Recommended base URL | Port |
|----------------|---------------------|------|
| You (browser, curl, IDE) on the host | `http://127.0.0.1:18000` | **18000** |
| Gateway from host (test stack) | `http://127.0.0.1:18080` | **18080** |
| External compose stacks (Option 3 gateway, live stack) | `http://unified-api-gateway` on network `rag_shared`, or `http://127.0.0.1:8080` from host | **8080** |
| Same compose project (e.g. `fin_rag`) | `http://unified_api:8000` | internal (container) |
| Live stack (`docker-compose.yml`) | `http://127.0.0.1:8000` | **8000** |
| Live gateway | `http://127.0.0.1:8080` | **8080** |

API **paths are identical** on direct and gateway URLs — only the host/port changes.

---

## Starting the service

### Test stack (default — port 18000)

Non-conflicting host ports; use when other services already bind 8000, 5432, 11434, etc.

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api unified_api_gateway
```

This starts `postgres`, `neo4j`, `chroma`, and `ollama` automatically via `depends_on`.

### Live stack (port 8000)

Use when default host ports are available:

```bash
# API only
docker compose --env-file .env up -d unified_api

# API + gateway (external consumers)
docker compose --env-file .env up -d unified_api unified_api_gateway

# Full stack (includes fin_rag)
docker compose --env-file .env up -d
```

### Local development (no Docker for the API process)

Requires databases running via compose:

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d postgres neo4j chroma ollama
cd unified_api && uv sync && uv run uvicorn unified_api.main:app --host 0.0.0.0 --port 8000
```

When running uvicorn on the host, use `http://127.0.0.1:8000` (not 18000).

---

## Verify the service is up

### Root health (test stack — port 18000)

```bash
curl -fsS http://127.0.0.1:18000/health
# {"status":"ok","service":"unified-api"}
```

### Per-service health (direct — port 18000)

```bash
curl -fsS http://127.0.0.1:18000/llm-service/health
curl -fsS http://127.0.0.1:18000/doc-processing/health
curl -fsS http://127.0.0.1:18000/core-rag/health
curl -fsS http://127.0.0.1:18000/ra-literag/health
curl -fsS http://127.0.0.1:18000/temporal-graph/health
curl -fsS http://127.0.0.1:18000/temporal-graph-openai/health
curl -fsS http://127.0.0.1:18000/temporal-graph-traversal/health
```

### Via gateway (test stack — port 18080)

Same paths, gateway port:

```bash
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/llm-service/health
```

### Live stack equivalents

Replace `18000` → `8000` and `18080` → `8080` when using `docker-compose.yml`.

---

## Interactive docs and OpenAPI

| Resource | URL (test stack) | URL (live stack) |
|----------|------------------|------------------|
| Swagger UI | [http://127.0.0.1:18000/docs](http://127.0.0.1:18000/docs) | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| ReDoc | [http://127.0.0.1:18000/redoc](http://127.0.0.1:18000/redoc) | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) |
| Live OpenAPI JSON | [http://127.0.0.1:18000/openapi.json](http://127.0.0.1:18000/openapi.json) | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) |
| Frozen spec (repo) | [../openapi/openapi.json](../openapi/openapi.json) | same |

Gateway serves the same docs at **18080** (test) or **8080** (live).

---

## Route prefixes

All merged services share one process. Prepend the prefix to every path:

| Feature | Prefix | Example |
|---------|--------|---------|
| LLM gateway | `/llm-service` | `POST /llm-service/llm/complete` |
| Document processing | `/doc-processing` | `POST /doc-processing/documents/pdf-to-markdown` |
| Core RAG graph | `/core-rag` | `POST /core-rag/api/query` |
| RA LightRAG | `/ra-literag` | `POST /ra-literag/query` |
| Temporal graph | `/temporal-graph` | `POST /temporal-graph/v1/collections` |
| Temporal graph (OpenAI) | `/temporal-graph-openai` | `POST /temporal-graph-openai/v1/ingest/jobs` |
| RAQE traversal | `/temporal-graph-traversal` | `POST /temporal-graph-traversal/query/ask` |

Full route list and examples: [api-overview.md](./api-overview.md).

---

## Calling from code

### Host machine (Python example — test stack)

```python
import httpx

BASE = "http://127.0.0.1:18000"

r = httpx.get(f"{BASE}/health")
r.raise_for_status()

r = httpx.post(
    f"{BASE}/llm-service/llm/complete",
    json={
        "provider": "openai",
        "messages": [{"role": "user", "content": "Hello"}],
    },
    timeout=120.0,
)
```

### External Docker compose (via gateway)

Set in the consumer service:

```bash
UNIFIED_API_BASE_URL=http://unified-api-gateway
LLM_SERVICE_BASE_URL=http://unified-api-gateway/llm-service
```

From host with test stack gateway: `http://127.0.0.1:18080`. From another container on the same host: `http://host.docker.internal:18080` (see [cross-compose-integration.md](./cross-compose-integration.md)).

### Environment variable reference

| Variable | Typical value | Used by |
|----------|---------------|---------|
| `UNIFIED_API_PUBLIC_URL` | `http://unified-api-gateway` | Documented consumer default (`.env.example`) |
| `UNIFIED_API_GATEWAY_PORT` | `8080` (live) / **18080** (test host) | Host port for gateway |
| `LLM_SERVICE_BASE_URL` | `http://unified_api:8000/llm-service` | `fin_rag` inside this compose file (internal port always 8000) |

---

## Logs and troubleshooting

```bash
# Test stack
docker compose -f docker-compose-test.yaml --env-file .env logs -f unified_api
docker compose -f docker-compose-test.yaml --env-file .env ps
```

| Symptom | Check |
|---------|--------|
| Connection refused on `:18000` | `docker compose -f docker-compose-test.yaml ps` — is `unified_api` healthy? |
| Connection refused on `:18080` | Start `unified_api_gateway`; it depends on `unified_api` |
| Port conflict on live stack `:8000` | Use test stack (`18000`) or free the conflicting host port |
| Neo4j auth errors | `NEO4J_PASSWORD` in `.env` (≥ 8 chars); may need fresh Neo4j volume |
| Slow first request | Ollama / model cold start; see [compose-runbook.md](../compose-runbook.md) |

---

## Stop the service

```bash
# Test stack — stop API + gateway, keep databases
docker compose -f docker-compose-test.yaml --env-file .env stop unified_api unified_api_gateway

# Test stack — stop everything
docker compose -f docker-compose-test.yaml --env-file .env down
```

---

## Related docs

- [README.md](./README.md) — run locally and in Docker
- [api-overview.md](./api-overview.md) — routes, health checks, examples
- [openapi.md](./openapi.md) — OpenAPI exports for client generation
- [cross-compose-integration.md](./cross-compose-integration.md) — external compose stacks and gateway
- [configuration.md](./configuration.md) — environment variables
- [compose-runbook.md](../compose-runbook.md) — full operational runbook
