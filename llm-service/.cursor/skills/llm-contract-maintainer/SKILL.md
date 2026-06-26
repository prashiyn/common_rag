# LLM Contract Maintainer

Use this skill when changing `/llm` routes or schemas.

## Objectives

1. Preserve backward compatibility for `/llm/*`.
2. Keep OpenAPI snapshot and generated spec synchronized.
3. Ensure tests cover both route behavior and contract shape.

## Required steps

1. Run route tests:
   - `uv run python -m pytest tests/test_llm_routes.py -q`
2. Regenerate openapi:
   - `PYTHONPATH=src uv run python -c "import json; from llm_service.main import app; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"`
3. If schema changes are intentional, update snapshot:
   - copy `openapi.json` to `openapi.snapshot.json`
4. Run contract test:
   - `uv run python -m pytest tests/test_openapi_contract.py -q`
