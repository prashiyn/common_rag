# OpenAPI Specs

This folder contains the generated OpenAPI spec for the FinSage RAG API so other services can integrate without importing the server code.

## Files

- `openapi.json`: canonical OpenAPI spec (JSON)
- `openapi.yaml`: same spec in YAML form

Both files are generated from `src/server.py` (FastAPI) and should be regenerated whenever API routes or request/response models change.

## Regenerate

From the project root:

```bash
PYTHONPATH=src uv run python script/generate_openapi.py
```

This overwrites:
- `openapi/openapi.json`
- `openapi/openapi.yaml`

## Notes for integrators

- **Auth**: Most endpoints require `Authorization: Bearer <token>` (see `bearer_token` in config or env `BEARER_TOKEN`).
- **Collection-scoped**: The API is **per-collection**. Endpoints that query RAG require `collection_name` (either in JSON body or query param, as defined in the spec).
- **Ingestion**: `POST /load-data` creates/updates a collection by ingesting chunk payloads.

## Unified LLM gateway (upstream)

`fin_rag` calls the merged **unified API** for LLM completions (`LLM_SERVICE_BASE_URL=http://unified_api:8000/llm-service`).

Use the monorepo OpenAPI slice (paths include the `/llm-service` prefix):

- [`../../docs/openapi/by-service/llm-service.json`](../../docs/openapi/by-service/llm-service.json)
- [`../../docs/openapi/by-service/llm-service.yaml`](../../docs/openapi/by-service/llm-service.yaml)

See [`../../docs/unified-api/openapi.md`](../../docs/unified-api/openapi.md). The local `llm_service_openapi.json` (if present) is a **legacy** standalone contract — do not use it for new unified integrations.

