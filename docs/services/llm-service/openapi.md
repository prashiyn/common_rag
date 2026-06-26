# OpenAPI — llm-service

Frozen snapshot: [../../openapi/llm-service.json](../../openapi/llm-service.json)

## Unified API paths

Prepend `/llm-service` to all paths in the snapshot. Example:

| Snapshot path | Unified path |
|---------------|--------------|
| `POST /llm/complete` | `POST /llm-service/llm/complete` |
| `GET /health` | `GET /llm-service/health` |

## Regenerate (standalone)

```bash
cd llm-service
PYTHONPATH=src uv run python -c \
  "import json; from llm_service.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

Copy to `docs/openapi/llm-service.json` when the contract changes.
