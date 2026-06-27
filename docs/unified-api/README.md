# Unified API

Single FastAPI process that mounts all seven application services under path prefixes. Source lives in `unified_api/` at the repo root.

**Default host access:** `http://127.0.0.1:18000` (test stack via `docker-compose-test.yaml`). Live stack uses port **8000** when host ports are free — see [access-guide.md](./access-guide.md).

## Run with Docker Compose (recommended)

From repo root, with `.env` configured:

```bash
# Test stack — default for development (host port 18000)
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api unified_api_gateway

# Health check
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18080/health   # via gateway
curl -fsS http://127.0.0.1:18000/llm-service/health
```

`unified_api` depends on **postgres**, **neo4j**, **chroma**, and **ollama** being healthy. See [compose-runbook.md](../compose-runbook.md) for Ollama first-time model setup.

### Live stack (port 8000)

Use when default host ports are available and you want the production port layout:

```bash
docker compose --env-file .env up -d unified_api unified_api_gateway
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/health   # via gateway
```

## Run locally (development)

Requires infrastructure databases running (e.g. test stack databases or `docker compose up -d postgres neo4j chroma ollama`).

```bash
cd unified_api
uv sync
uv run uvicorn unified_api.main:app --host 0.0.0.0 --port 8000
```

Set `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` so internal service calls resolve to the in-process LLM routes.

With `LLM_CLIENT_MODE=inprocess` (default in Docker Compose), merged services call `llm_service.runtime` directly instead of HTTP loopback.

## Build the Docker image

```bash
docker compose -f docker-compose-test.yaml --env-file .env build unified_api
```

## Logs

```bash
docker compose -f docker-compose-test.yaml --env-file .env logs -f unified_api
```

Host files: `unified_api/logs/uvicorn.log` (bind-mounted from compose).

## Nirmana MFO (this repo) as a consumer

The MFO platform does **not** run `unified_api`, `ollama`, or legacy `doc_processing` / `llm-service` containers in its own `docker-compose.yml`. Start the unified API stack separately, then configure MFO `.env`:

| MFO variable | Purpose |
|--------------|---------|
| `UNIFIED_API_BASE_URL` | Root URL (`http://127.0.0.1:18000` on host with test stack) |
| `DOC_PROCESSING_BASE_URL` | Document chunking (`POST /documents/chunk`) |
| `LLM_SERVICE_BASE_URL` | LLM gateway (future phases) |
| Other `*_BASE_URL` vars | RAG / graph services (future phases) |

Celery worker (Docker) reaches the host unified API via `http://host.docker.internal:18000/...` — see MFO `docker-compose.yml` and [cross-compose-integration.md](./cross-compose-integration.md) Option 1.

Verify from MFO repo root:

```bash
./scripts/verify_unified_api.sh
./scripts/verify_doc_processing.sh
```

## Related docs

- [access-guide.md](./access-guide.md) — how to start, reach, and verify the unified API
- [configuration.md](./configuration.md) — environment variables
- [api-overview.md](./api-overview.md) — prefixes and health checks
- [migration-notes.md](./migration-notes.md) — URL changes for external integrators
- [cross-compose-integration.md](./cross-compose-integration.md) — calling unified API from another Docker Compose project
- [openapi.md](./openapi.md) — OpenAPI exports and client consumption
