# OpenAPI specifications

## Unified API (use for new integrations)

| File | Description |
|------|-------------|
| [openapi.json](./openapi.json) | **Canonical** full unified contract (all route prefixes) |
| [openapi.yaml](./openapi.yaml) | Same spec in YAML |
| [unified-api.json](./unified-api.json) | Alias of `openapi.json` |
| [unified-api.yaml](./unified-api.yaml) | Alias of `openapi.yaml` |
| [by-service/](./by-service/) | Per-prefix slices for downstream services (e.g. `fin_rag` → `llm-service.json`) |

Regenerate after route changes:

```bash
cd unified_api && uv run python scripts/export_openapi.py
```

Details: [../unified-api/openapi.md](../unified-api/openapi.md)

## Live spec (authoritative at runtime)

When the unified API is running:

```bash
curl -s http://127.0.0.1:8000/openapi.json | jq '.paths | keys | length'
```

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The live spec matches the frozen `openapi.json` export when generated from the same commit.

## Legacy snapshots (pre-unification paths)

These JSON files were exported from **standalone** services before the unified merge. Paths do **not** include unified prefixes (`/llm-service`, etc.):

| File | Service |
|------|---------|
| [llm-service.json](./llm-service.json) | llm-service (legacy) |
| [doc-processing.json](./doc-processing.json) | doc_processing (legacy) |
| [core-rag-graph.json](./core-rag-graph.json) | core_rag_graph (legacy) |
| [ra-literag.json](./ra-literag.json) | ra_literag (legacy) |
| [temporal-graph.json](./temporal-graph.json) | temporial_graph (legacy) |
| [temporal-graph-openai.json](./temporal-graph-openai.json) | temporial_graph_openai (legacy) |

For current integrations, use `openapi.json` or `by-service/` — see [../unified-api/migration-notes.md](../unified-api/migration-notes.md).

## Regenerating legacy snapshots

Only needed for historical comparison. From each service directory (standalone dev):

```bash
# llm-service
cd llm-service && PYTHONPATH=src uv run python -c \
  "import json; from llm_service.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"

# doc_processing
cd doc_processing && uv run python -c \
  "import json; from doc_processing.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

Copy updated files into `docs/openapi/` when comparing legacy contracts.
