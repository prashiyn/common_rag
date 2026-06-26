# ra-literag FastAPI service

> **Unified API:** routes are mounted at `/ra-literag` on port **8000** (test: **18000**).  
> See [unified-api/migration-notes.md](../../unified-api/migration-notes.md) for URL mapping.

**ra-literag** is the HTTP wrapper around in-repo **RAGAnything** (LightRAG + multimodal parsing). It exposes query, ingest, and config APIs. All LLM completions and embeddings go through the unified **llm-service** routes (`/llm-service`).

## Documentation

| Document | Purpose |
|----------|---------|
| [service.md](./service.md) | Full service guide (install, run, endpoints) |
| [config-reference.md](./config-reference.md) | Environment variable reference |
| [offline-setup.md](./offline-setup.md) | Offline / air-gapped setup |
| [batch-processing.md](./batch-processing.md) | Batch ingest workflows |
| [openapi.md](./openapi.md) | OpenAPI notes |
| [../../openapi/ra-literag.json](../../openapi/ra-literag.json) | Frozen OpenAPI snapshot |

## Quick health check (unified stack)

```bash
curl -fsS http://127.0.0.1:8000/ra-literag/health
curl -fsS http://127.0.0.1:8000/ra-literag/ready
```

## Standalone development

```bash
cd ra_literag
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set `LLM_SERVICE_BASE_URL=http://localhost:8000/llm-service` when using the unified server for LLM calls.
