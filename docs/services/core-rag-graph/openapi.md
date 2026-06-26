# OpenAPI — core RAG graph

Frozen snapshot: [../../openapi/core-rag-graph.json](../../openapi/core-rag-graph.json)

## Unified API paths

Prepend `/core-rag` to all paths in the snapshot. Example:

| Snapshot path | Unified path |
|---------------|--------------|
| `POST /api/query` | `POST /core-rag/api/query` |
| `GET /health` | `GET /core-rag/health` |

## Regenerate (standalone)

```bash
cd core_rag_graph
uv run python -c \
  "import json; from graph_server import app; open('docs/openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

Copy to `docs/openapi/core-rag-graph.json` when the contract changes.
