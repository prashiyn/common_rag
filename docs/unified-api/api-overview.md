# Unified API overview

Base URL (live stack): `http://127.0.0.1:8000`  
Base URL (test stack): `http://127.0.0.1:18000`

OpenAPI: `GET /openapi.json` — Swagger UI at `/docs`

## Route prefixes

| Service | Prefix | Health endpoints |
|---------|--------|------------------|
| Unified server | *(root)* | `GET /health` |
| llm-service | `/llm-service` | `GET /llm-service/health`, `GET /llm-service/health/ready` |
| doc_processing | `/doc-processing` | `GET /doc-processing/health` |
| core_rag_graph | `/core-rag` | `GET /core-rag/health`, `GET /core-rag/health/ready` |
| ra_literag | `/ra-literag` | `GET /ra-literag/health`, `GET /ra-literag/ready` |
| temporial_graph | `/temporal-graph` | `GET /temporal-graph/health`, `GET /temporal-graph/v1/health/llm`, `GET /temporal-graph/v1/health/neo4j` |
| temporial_graph_openai | `/temporal-graph-openai` | `GET /temporal-graph-openai/health` |
| temporial_graph_traversal | `/temporal-graph-traversal` | `GET /temporal-graph-traversal/health` |

## Smoke-test curls (live stack)

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/llm-service/health
curl -fsS http://127.0.0.1:8000/doc-processing/health
curl -fsS http://127.0.0.1:8000/core-rag/health
curl -fsS http://127.0.0.1:8000/ra-literag/health
curl -fsS http://127.0.0.1:8000/temporal-graph/health
curl -fsS http://127.0.0.1:8000/temporal-graph-openai/health
curl -fsS http://127.0.0.1:8000/temporal-graph-traversal/health
```

## Primary API examples

| Operation | Method and path |
|-----------|-----------------|
| LLM completion | `POST /llm-service/llm/complete` |
| OpenAI-compatible chat | `POST /llm-service/v1/chat/completions` |
| PDF to markdown | `POST /doc-processing/documents/pdf-to-markdown` |
| Graph query | `POST /core-rag/api/query` |
| RAG query | `POST /ra-literag/query` |
| Temporal collections | `POST /temporal-graph/v1/collections` |
| Ingest job | `POST /temporal-graph-openai/v1/ingest/jobs` |
| RAQE ask | `POST /temporal-graph-traversal/query/ask` |

Request and response **schemas are unchanged** from the standalone services; only the URL prefix changed. See [migration-notes.md](./migration-notes.md).

## OpenAPI sources

- **Live (authoritative):** `GET /openapi.json` on the running unified server (~79 paths).
- **Frozen snapshots:** [../openapi/](../openapi/) — pre-unification path layouts for contract comparison.

## Middleware notes

These middlewares are active on the unified app:

- `CollectionIdMiddleware` — `core_rag_graph` collection ID handling
- `CollectionNameExposeMiddleware` — `temporial_graph`
- `CollectionWireResponseMiddleware`, `CollectionPathRewriteMiddleware` — `temporial_graph_openai`
- `CollectionNamespaceMiddleware` — `temporial_graph_traversal` (RAQE)
