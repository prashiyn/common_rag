# OpenAPI specifications

## Live spec (authoritative)

When the unified API is running:

```bash
curl -s http://127.0.0.1:8000/openapi.json | jq '.paths | keys | length'
```

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The live spec includes **all route prefixes** (`/llm-service`, `/doc-processing`, etc.) and is the source of truth for integrators.

## Frozen snapshots (pre-unification paths)

These JSON files were exported from standalone services before the unified merge. They preserve the original path layout for contract comparison:

| File | Service |
|------|---------|
| [llm-service.json](./llm-service.json) | llm-service |
| [doc-processing.json](./doc-processing.json) | doc_processing |
| [core-rag-graph.json](./core-rag-graph.json) | core_rag_graph |
| [ra-literag.json](./ra-literag.json) | ra_literag |
| [temporal-graph.json](./temporal-graph.json) | temporial_graph |
| [temporal-graph-openai.json](./temporal-graph-openai.json) | temporial_graph_openai |

To call these APIs today, prepend the unified prefix — see [../unified-api/migration-notes.md](../unified-api/migration-notes.md).

## Regenerating snapshots

From each service directory (standalone dev):

```bash
# llm-service
cd llm-service && PYTHONPATH=src uv run python -c \
  "import json; from llm_service.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"

# doc_processing
cd doc_processing && uv run python -c \
  "import json; from doc_processing.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

Copy updated files into `docs/openapi/` when contracts change.
