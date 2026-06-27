# Common Services Documentation

This repository runs a **unified FastAPI server** (`unified_api`) that exposes all RAG, document-processing, LLM gateway, and temporal-graph features in one process on port **8000**. Shared infrastructure (Postgres, Neo4j, Chroma, Ollama) is started via Docker Compose. `fin_rag` remains a separate service on port **6005**.

Implementation details and migration history: [unified-api-implementation-plan.md](./unified-api-implementation-plan.md).

## Quick start

```bash
cp .env.example .env
# Edit NEO4J_PASSWORD and POSTGRES_PASSWORD (non-default values)
docker compose --env-file .env up -d unified_api
curl http://127.0.0.1:8000/health
```

Interactive API docs (when the server is running): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Documentation map

| Document | Audience | Description |
|----------|----------|-------------|
| [compose-runbook.md](./compose-runbook.md) | Operators | Docker Compose, test stack, Ollama, logs, builds |
| [unified-api/README.md](./unified-api/README.md) | Developers | Run unified server locally or in Docker |
| [unified-api/configuration.md](./unified-api/configuration.md) | Operators | Environment variables |
| [unified-api/api-overview.md](./unified-api/api-overview.md) | Integrators | Route prefixes and health endpoints |
| [unified-api/access-guide.md](./unified-api/access-guide.md) | Operators / integrators | How to start, reach, and verify the unified API |
| [unified-api/openapi.md](./unified-api/openapi.md) | Integrators | Unified OpenAPI exports and client consumption |
| [unified-api/cross-compose-integration.md](./unified-api/cross-compose-integration.md) | Integrators | Call unified API from a separate Docker Compose stack |
| [unified-api/migration-notes.md](./unified-api/migration-notes.md) | Integrators | Old microservice URLs → unified paths |
| [repository-layout.md](./repository-layout.md) | Maintainers | Monorepo directory layout decision (Option A vs `packages/`) |
| [services/](./services/) | Per-feature | Deep dives per merged service |
| [openapi/](./openapi/) | Integrators | Frozen OpenAPI snapshots + live spec notes |

## Unified API route prefixes

| Feature area | Prefix | Example |
|--------------|--------|---------|
| LLM gateway | `/llm-service` | `POST /llm-service/llm/complete` |
| Document processing | `/doc-processing` | `POST /doc-processing/documents/pdf-to-markdown` |
| Core RAG graph | `/core-rag` | `POST /core-rag/api/query` |
| RA LightRAG | `/ra-literag` | `POST /ra-literag/query` |
| Temporal graph | `/temporal-graph` | `POST /temporal-graph/v1/collections` |
| Temporal graph (OpenAI) | `/temporal-graph-openai` | `POST /temporal-graph-openai/v1/ingest/jobs` |
| Temporal graph traversal (RAQE) | `/temporal-graph-traversal` | `POST /temporal-graph-traversal/query/ask` |

## Service documentation

- [llm-service](./services/llm-service/)
- [doc-processing](./services/doc-processing/)
- [core-rag-graph](./services/core-rag-graph/)
- [ra-literag](./services/ra-literag/)
- [temporal-graph](./services/temporal-graph/)
- [temporal-graph-openai](./services/temporal-graph-openai/)
- [temporal-graph-traversal](./services/temporal-graph-traversal/)
- [fin-rag](./services/fin-rag/) (separate Compose service, not merged)
