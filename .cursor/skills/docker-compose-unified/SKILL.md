---
name: docker-compose-unified
description: Creates and maintains a unified Docker Compose stack with unified_api (all seven merged services on port 8000), fin_rag (separate on 6005), and shared databases (chroma, neo4j; postgres for fin_rag and ra_literag only). Use when adding services, changing container ports, wiring environment variables, or updating compose dependencies.
---

# Unified Docker Compose Skill

## Goal

Maintain one compose stack that launches **unified_api** (all seven merged application services) plus **fin_rag** and shared databases:
- `postgres`
- `neo4j`
- `chroma`
- `ollama`

Canonical documentation: [docs/README.md](../../docs/README.md)

## Service Mapping

| Compose service | Host port (live) | Host port (test) | Notes |
|-----------------|------------------|------------------|-------|
| `unified_api` | `8000` | `18000` | Merges llm-service, doc_processing, core_rag_graph, ra_literag, temporial_graph, temporial_graph_openai, temporial_graph_traversal |
| `fin_rag` | `6005` | `16005` | Separate service; calls `http://unified_api:8000/llm-service` |

### Unified API route prefixes

| Feature | Prefix |
|---------|--------|
| llm-service | `/llm-service` |
| doc_processing | `/doc-processing` |
| core_rag_graph | `/core-rag` |
| ra_literag | `/ra-literag` |
| temporial_graph | `/temporal-graph` |
| temporial_graph_openai | `/temporal-graph-openai` |
| temporial_graph_traversal | `/temporal-graph-traversal` |

## Secrets & env files

1. Never commit literals for DB passwords inside `docker-compose.yml`.
2. Add a **repo-root** `.env` (gitignored): copy `.env.example` and set `POSTGRES_PASSWORD`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`. Compose reads this automatically for `${VAR}` interpolation.
3. Per-service `.env` files are gitignored templates; tracked `*.env.example` / `ra_literag/env.example` hold non-secret defaults. Compose `environment:` injects unified credentials so services stay aligned with the root file.
4. `ra_literag` has no `env_file` in compose; it receives DB vars only from the compose `environment` block (same root variables). Postgres there backs LightRAG / RAG-Anything storage; **schema is managed by the application**, not Alembic in this stack.
5. **`core_rag_graph`** does **not** use Postgres in compose; it depends on `neo4j` and `chroma` only (via `unified_api`).
6. **Postgres**: one server, **separate logical databases** for `fin_rag` and `ra_literag` (`POSTGRES_DB_FIN_RAG`, `POSTGRES_DB_RA_LITERAG`). Init script `docker/postgres-init/01-create-databases.sh` runs only on a **fresh** `./db/postgres_data` volume; existing volumes need manual `CREATE DATABASE` or a reset.
7. **Alembic (`fin_rag` only):** service `fin_rag_migrate` runs `alembic upgrade head` once Postgres is healthy, then exits. `fin_rag` uses `depends_on: fin_rag_migrate: condition: service_completed_successfully` so the API never starts before migrations succeed. Requires Docker Compose v2 with the completed-successfully condition.

## Database Wiring

- **Postgres**
  - Host inside compose network: `postgres`
  - Port: `5432`
  - Bootstrap DB for healthchecks: `POSTGRES_BOOTSTRAP_DB` (default `postgres`)
  - App DBs: `fin_rag` -> `POSTGRES_DB_FIN_RAG`, `ra_literag` -> `POSTGRES_DB_RA_LITERAG` (override in repo-root `.env`)
  - `fin_rag` URL: `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB_FIN_RAG}`
- **Neo4j**
  - Host: `neo4j`
  - Bolt URL: `bolt://neo4j:7687`
  - Browser port: `7474`
- **Chroma**
  - Host: `chroma`
  - Internal port: `8000`

## Internal LLM URL

Inside `unified_api` container: `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service`

From other containers (e.g. `fin_rag`): `http://unified_api:8000/llm-service`

## Authoring Rules

1. Keep all services in one root `docker-compose.yml`.
2. Use `depends_on` with health checks for database readiness.
3. Keep persistent named volumes for each database.
4. Prefer explicit environment variables over hidden defaults.
5. `unified_api` uses `unified_api/Dockerfile.compose`.
6. Keep compose YAML compatible with Docker Compose v2 (no top-level `version` key required).

## Testing the unified API (same `docker-compose.yml`)

```bash
docker compose --env-file .env up -d unified_api
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/llm-service/health
```

Add `--build` when you changed `unified_api/Dockerfile.compose` or application code.

**Test stack:**

```bash
docker compose -f docker-compose-test.yaml --env-file .env build unified_api
docker compose -f docker-compose-test.yaml --env-file .env up -d unified_api
curl -fsS http://127.0.0.1:18000/health
```

**Live / full stack:** `docker compose up -d` (unified_api + fin_rag + databases + ollama).

**Test stack:** `docker-compose-test.yaml` uses project name `common-test`, `./test_db/*` volumes, **no fixed `container_name`**, and **different published host ports** (unified_api `18000`, Postgres `15432`, Chroma `18001`, etc.) so test and live can run together.

## Validation Checklist

- Run `docker compose config` and fix schema issues.
- Confirm no host port conflicts.
- Confirm `unified_api` command is `uvicorn unified_api.main:app`.
- Confirm all DB hostnames use compose service names (`postgres` where used, `neo4j`, `chroma`), not `localhost`.
- Smoke-test all health endpoints — see [docs/compose-runbook.md](../../docs/compose-runbook.md).
