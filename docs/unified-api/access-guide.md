# Accessing the unified API

How to reach the unified API from your machine, from other Docker containers, and from external compose stacks.

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
| You (browser, curl, IDE) on the host | `http://127.0.0.1:8000` | **8000** |
| External compose stacks (Option 3 gateway) | `http://unified-api-gateway` on network `rag_shared`, or `http://127.0.0.1:8080` from host | **8080** |
| Same compose project (e.g. `fin_rag`) | `http://unified_api:8000` | internal |
| Test stack (`docker-compose-test.yaml`) | `http://127.0.0.1:18000` | **18000** |
| Test gateway | `http://127.0.0.1:18080` | **18080** |

API **paths are identical** on direct and gateway URLs — only the host/port changes.

---

## Starting the service

### Live stack (recommended)

**API only** (local development):

```bash
docker compose --env-file .env up -d unified_api
```

**API + gateway** (when external services consume unified API):

```bash
docker compose --env-file .env up -d unified_api unified_api_gateway
```

This starts `postgres`, `neo4j`, `chroma`, and `ollama` automatically via `depends_on`.

**Full stack** (includes `fin_rag`):

```bash
docker compose --env-file .env up -d
```

### Test stack (non-conflicting ports)

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api unified_api_gateway
```

### Local development (no Docker for the API process)

Requires databases running via compose:

```bash
docker compose --env-file .env up -d postgres neo4j chroma ollama
cd unified_api && uv sync && uv run uvicorn unified_api.main:app --host 0.0.0.0 --port 8000
```

---

## Verify the service is up

### Root health

```bash
curl -fsS http://127.0.0.1:8000/health
# {"status":"ok","service":"unified-api"}
```

### Per-service health (direct — port 8000)

```bash
curl -fsS http://127.0.0.1:8000/llm-service/health
curl -fsS http://127.0.0.1:8000/doc-processing/health
curl -fsS http://127.0.0.1:8000/core-rag/health
curl -fsS http://127.0.0.1:8000/ra-literag/health
curl -fsS http://127.0.0.1:8000/temporal-graph/health
curl -fsS http://127.0.0.1:8000/temporal-graph-openai/health
curl -fsS http://127.0.0.1:8000/temporal-graph-traversal/health
```

### Via gateway (port 8080)

Same paths, different port:

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/llm-service/health
```

---

## Interactive docs and OpenAPI

| Resource | URL (live stack) |
|----------|------------------|
| Swagger UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| ReDoc | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) |
| Live OpenAPI JSON | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) |
| Frozen spec (repo) | [../openapi/openapi.json](../openapi/openapi.json) |

Gateway serves the same docs at port **8080** (e.g. `http://127.0.0.1:8080/docs`).

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

### Host machine (Python example)

```python
import httpx

BASE = "http://127.0.0.1:8000"

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

Join network `rag_shared` (see [cross-compose-integration.md](./cross-compose-integration.md)).

### Environment variable reference

| Variable | Typical value | Used by |
|----------|---------------|---------|
| `UNIFIED_API_PUBLIC_URL` | `http://unified-api-gateway` | Documented consumer default (`.env.example`) |
| `UNIFIED_API_GATEWAY_PORT` | `8080` | Host port for gateway |
| `LLM_SERVICE_BASE_URL` | `http://unified_api:8000/llm-service` | `fin_rag` inside this compose file |

---

## Logs and troubleshooting

```bash
# Follow unified API logs
docker compose --env-file .env logs -f unified_api

# Gateway logs
docker compose --env-file .env logs -f unified_api_gateway

# Container status
docker compose --env-file .env ps
```

| Symptom | Check |
|---------|--------|
| Connection refused on `:8000` | `docker compose ps` — is `unified_api` healthy? |
| Connection refused on `:8080` | Start `unified_api_gateway`; it depends on `unified_api` |
| Neo4j auth errors | `NEO4J_PASSWORD` in `.env` (≥ 8 chars); may need fresh Neo4j volume |
| Slow first request | Ollama / model cold start; see [compose-runbook.md](../compose-runbook.md) |

---

## Stop the service

```bash
# Stop API + gateway, keep databases
docker compose --env-file .env stop unified_api unified_api_gateway

# Stop everything
docker compose --env-file .env down
```

---

## Related docs

- [README.md](./README.md) — run locally and in Docker
- [api-overview.md](./api-overview.md) — routes, health checks, examples
- [openapi.md](./openapi.md) — OpenAPI exports for client generation
- [cross-compose-integration.md](./cross-compose-integration.md) — external compose stacks and gateway
- [configuration.md](./configuration.md) — environment variables
- [compose-runbook.md](../compose-runbook.md) — full operational runbook
