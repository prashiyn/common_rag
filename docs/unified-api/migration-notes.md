# Migration notes: microservices → unified API

External systems that previously called separate host ports should update **base URLs only**. Request and response JSON schemas are **unchanged**.

**Default development stack** uses `docker-compose-test.yaml` with host port **18000**.

## Test stack (`docker-compose-test.yaml`) — default

| Old base URL | Service | New base URL |
|--------------|---------|--------------|
| `http://host:8020` | llm-service | `http://host:18000/llm-service` |
| `http://host:8010` | doc_processing | `http://host:18000/doc-processing` |
| `http://host:20050` | core_rag_graph | `http://host:18000/core-rag` |
| `http://host:8000` | ra_literag | `http://host:18000/ra-literag` |
| `http://host:8082` | temporial_graph | `http://host:18000/temporal-graph` |
| `http://host:8080` | temporial_graph_openai | `http://host:18000/temporal-graph-openai` |
| `http://host:8090` | temporial_graph_traversal | `http://host:18000/temporal-graph-traversal` |

## Live stack (`docker-compose.yml`)

Same path prefixes; host port **8000**:

| Old base URL | Service | New base URL |
|--------------|---------|--------------|
| `http://host:8020` | llm-service | `http://host:8000/llm-service` |
| `http://host:8010` | doc_processing | `http://host:8000/doc-processing` |
| `http://host:20050` | core_rag_graph | `http://host:8000/core-rag` |
| `http://host:8000` | ra_literag | `http://host:8000/ra-literag` |
| `http://host:8082` | temporial_graph | `http://host:8000/temporal-graph` |
| `http://host:8080` | temporial_graph_openai | `http://host:8000/temporal-graph-openai` |
| `http://host:8090` | temporial_graph_traversal | `http://host:8000/temporal-graph-traversal` |

## Path mapping examples (test stack — port 18000)

| Old | New |
|-----|-----|
| `POST http://host:8020/llm/complete` | `POST http://host:18000/llm-service/llm/complete` |
| `GET http://host:8010/health` | `GET http://host:18000/doc-processing/health` |
| `POST http://host:20050/api/query` | `POST http://host:18000/core-rag/api/query` |
| `POST http://host:8000/query` | `POST http://host:18000/ra-literag/query` |
| `POST http://host:8082/v1/collections` | `POST http://host:18000/temporal-graph/v1/collections` |
| `POST http://host:8080/v1/ingest/jobs` | `POST http://host:18000/temporal-graph-openai/v1/ingest/jobs` |
| `POST http://host:8090/query/ask` | `POST http://host:18000/temporal-graph-traversal/query/ask` |

Live stack: replace `18000` with `8000` in the URLs above.

## Internal Docker URLs (compose)

| Old | New |
|-----|-----|
| `http://llm-service:8001` | `http://localhost:8000/llm-service` (inside `unified_api` container) |
| `http://llm-service:8001` | `http://unified_api:8000/llm-service` (from other containers, e.g. `fin_rag`) |

## Unchanged

- `fin_rag` remains on port **6005** (test: **16005**).
- Postgres, Neo4j, Chroma, Ollama host ports unchanged.
- Database schemas per service unchanged.
