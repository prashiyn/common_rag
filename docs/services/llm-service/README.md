# llm-service

> **Unified API:** routes are mounted at `/llm-service` on port **8000** (test: **18000**).  
> Canonical docs: [README.md](./README.md) · [openapi.md](./openapi.md) · [migration-notes](../../unified-api/migration-notes.md)

Standalone `/llm` gateway extracted from the monolith.

## Run

```bash
uv sync --extra dev
PYTHONPATH=src uv run python -m llm_service.main
```

## OpenAPI

Generate:

```bash
PYTHONPATH=src uv run python -c "import json; from llm_service.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```
