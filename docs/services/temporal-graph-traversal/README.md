# Reference-Aware Query Engine (RAQE)

> **Unified API:** routes are mounted at `/temporal-graph-traversal` on port **8000** (test: **18000**).  
> See [unified-api/migration-notes.md](../../unified-api/migration-notes.md) for URL mapping.

FastAPI service for reference-aware graph traversal queries.

## Documentation

| Document | Purpose |
|----------|---------|
| [reference-query-engine.md](./reference-query-engine.md) | RAQE design and query engine reference |
| [implementation-plan.md](./implementation-plan.md) | Phasewise implementation plan |
| [phase-guides/](./phase-guides/) | Phase-by-phase implementation guides |

## Quick health check (unified stack)

```bash
curl -fsS http://127.0.0.1:8000/temporal-graph-traversal/health
```

## Standalone development

```bash
cd temporial_graph_traversal
uv sync
uv run uvicorn raqe.main:app --host 0.0.0.0 --port 8090
```

Set `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` when using the unified server, or run standalone on port 8090.
