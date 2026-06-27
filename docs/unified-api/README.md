# Unified API

Single FastAPI process that mounts all seven application services under path prefixes. Source lives in `unified_api/` at the repo root.

## Run with Docker Compose (recommended)

From repo root, with `.env` configured:

```bash
# Unified API only
docker compose --env-file .env up -d unified_api

# Unified API + gateway for external compose consumers (Option 3)
docker compose --env-file .env up -d unified_api unified_api_gateway

# Health check
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/health   # via gateway
curl -fsS http://127.0.0.1:8000/llm-service/health
```

`unified_api` depends on **postgres**, **neo4j**, **chroma**, and **ollama** being healthy. See [compose-runbook.md](../compose-runbook.md) for Ollama first-time model setup.

### Test stack

```bash
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api
curl -fsS http://127.0.0.1:18000/health
```

## Run locally (development)

Requires infrastructure databases running (e.g. `docker compose up -d postgres neo4j chroma ollama`).

```bash
cd unified_api
uv sync
uv run uvicorn unified_api.main:app --host 0.0.0.0 --port 8000
```

Set `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` so internal service calls resolve to the in-process LLM routes.

With `LLM_CLIENT_MODE=inprocess` (default in Docker Compose), merged services call `llm_service.runtime` directly instead of HTTP loopback.

## Build the Docker image

```bash
docker compose --env-file .env build unified_api
```

## Logs

- Docker: `docker compose logs -f unified_api`
- Host files: `unified_api/logs/uvicorn.log` (bind-mounted from compose)

## Related docs

- [access-guide.md](./access-guide.md) — how to start, reach, and verify the unified API
- [configuration.md](./configuration.md) — environment variables
- [api-overview.md](./api-overview.md) — prefixes and health checks
- [migration-notes.md](./migration-notes.md) — URL changes for external integrators
- [cross-compose-integration.md](./cross-compose-integration.md) — calling unified API from another Docker Compose project
- [openapi.md](./openapi.md) — OpenAPI exports and client consumption
