# Unified API — OpenAPI specifications

Use these specs to generate clients, validate requests, or document integrations against the **unified API** on port **8000**.

## Files

| File | Use when |
|------|----------|
| [../openapi/openapi.json](../openapi/openapi.json) | You need **all** route prefixes in one contract (canonical) |
| [../openapi/openapi.yaml](../openapi/openapi.yaml) | Same as JSON; easier for some tooling |
| [../openapi/unified-api.json](../openapi/unified-api.json) | Alias of `openapi.json` |
| [../openapi/by-service/](../openapi/by-service/) | You only call **one** merged service (e.g. `fin_rag` → `llm-service.json`) |

### Per-service slices (`docs/openapi/by-service/`)

Each slice contains only paths under that unified prefix:

| File | Prefix | Example path |
|------|--------|--------------|
| `llm-service.json` | `/llm-service` | `POST /llm-service/llm/complete` |
| `doc-processing.json` | `/doc-processing` | `POST /doc-processing/documents/pdf-to-markdown` |
| `core-rag.json` | `/core-rag` | `POST /core-rag/api/query` |
| `ra-literag.json` | `/ra-literag` | `POST /ra-literag/query` |
| `temporal-graph.json` | `/temporal-graph` | `POST /temporal-graph/v1/collections` |
| `temporal-graph-openai.json` | `/temporal-graph-openai` | `POST /temporal-graph-openai/v1/ingest/jobs` |
| `temporal-graph-traversal.json` | `/temporal-graph-traversal` | `POST /temporal-graph-traversal/query/ask` |

All slices include `servers` for local and Docker Compose base URLs.

## Live spec (authoritative at runtime)

When the server is running:

```bash
curl -s http://127.0.0.1:8000/openapi.json | jq '.info.title, (.paths | keys | length)'
```

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Frozen files under `docs/openapi/` are regenerated from code and checked in CI/tests.

## Regenerate frozen exports

From the repo root:

```bash
cd unified_api
uv run python scripts/export_openapi.py
```

Validate without writing:

```bash
cd unified_api
uv run python scripts/export_openapi.py --check
```

## Consuming from another service

### HTTP base URL

| Environment | Base URL |
|-------------|----------|
| Local | `http://127.0.0.1:8000` |
| Docker Compose (e.g. `fin_rag`) | `http://unified_api:8000` |

Append the route path from the spec (paths already include the service prefix).

### Example: `fin_rag` calling LLM gateway

1. Copy or reference [../openapi/by-service/llm-service.json](../openapi/by-service/llm-service.json).
2. Set `LLM_SERVICE_BASE_URL=http://unified_api:8000/llm-service` in Compose.
3. Call `POST {LLM_SERVICE_BASE_URL}/llm/complete` (path from spec, base URL without trailing slash).

### Client generation (optional)

```bash
# OpenAPI Generator example — llm-service slice only
openapi-generator generate \
  -i docs/openapi/by-service/llm-service.json \
  -g python \
  -o /tmp/llm-client \
  --additional-properties=packageName=unified_llm_client
```

## Legacy standalone specs

Pre-unification snapshots (paths **without** unified prefixes) remain in [../openapi/](../openapi/README.md) for contract comparison. Do **not** use them for new integrations — use `unified-api.json` or `by-service/` instead.
