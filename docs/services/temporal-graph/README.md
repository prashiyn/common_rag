# Documentation index — temporal graph

> **Unified API:** routes are mounted at `/temporal-graph` on port **8000** (test: **18000**).  
> See [unified-api/migration-notes.md](../../unified-api/migration-notes.md) for URL mapping.

| Document | Purpose |
| -------- | ------- |
| [design.md](./design.md) | System design: mapping from OpenAI Temporal Agents and product enhancements to this implementation. |
| [developer-guide.md](./developer-guide.md) | Developer guide: multi-step retrieval, decay, ingestion, retrieval, jobs, extension points. |
| [openapi.md](./openapi.md) | HTTP API guide; machine-readable spec in [../../openapi/temporal-graph.json](../../openapi/temporal-graph.json). |
| [ontology.md](./ontology.md) | Ontology JSON: taxonomy, `subevent_overrides`, validation, JSON Schema. |
| [multi-project-spec.md](./multi-project-spec.md) | Project/collection tenancy model, naming conventions, persistent registry behavior. |

## Quick health check (unified stack)

```bash
curl -fsS http://127.0.0.1:8000/temporal-graph/health
```

## External references

- **HTTP LLM contract:** served at `/llm-service` on the unified API.
- Product mapping and notebooks remain in the `temporial_graph/docs/` source tree.
