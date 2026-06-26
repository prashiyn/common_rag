# Documentation — temporal graph (OpenAI variant)

> **Unified API:** routes are mounted at `/temporal-graph-openai` on port **8000** (test: **18000**).  
> See [unified-api/migration-notes.md](../../unified-api/migration-notes.md) for URL mapping.

| Document | Purpose |
|----------|---------|
| [developer.md](./developer.md) | Architecture, layout, configuration, running the API, ingestion and external services |
| [ontologies.md](./ontologies.md) | Authoring ontology JSON, JSON Schema rules, invalidation and predicate groups |
| [openapi.md](./openapi.md) | Human/agent-oriented API reference (collections, ingest, retrieve, health) |
| [canonical-events.md](./canonical-events.md) | Canonical event definitions |
| [financial-entity-schema.md](./financial-entity-schema.md) | Financial entity schema |
| [../../openapi/temporal-graph-openai.json](../../openapi/temporal-graph-openai.json) | Machine-readable OpenAPI 3.1 snapshot |

## Quick health check (unified stack)

```bash
curl -fsS http://127.0.0.1:8000/temporal-graph-openai/health
```

Ontology files are validated at load time against `temporal_graph/ontology/ontology.schema.json`. From the repo root you can also run:

```bash
uv run tg-validate-ontology ontologies/company_data.json
```
