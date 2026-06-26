# Config reference (populated from .env)

All application and LightRAG settings are loaded from environment variables (see project root `env.example`). This file lists every variable used by the FastAPI app and `app.config`.

## Server
| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind host for uvicorn |
| `PORT` | `8000` | Bind port |

## PostgreSQL (workspace config and optional LightRAG storage)
| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Host for Postgres (used for ra_litelag_config table) |
| `POSTGRES_PORT` | `5432` | Port |
| `POSTGRES_USER` | (empty) | User |
| `POSTGRES_PASSWORD` | (empty) | Password |
| `POSTGRES_DATABASE` | (empty) | Database (required for GET/POST /config/{workspace_id}) |

## LightRAG storage (multi-tenant via workspace)
| Variable | Default | Description |
|----------|---------|-------------|
| `LIGHTRAG_KV_STORAGE` | `JsonKVStorage` | KV storage class |
| `LIGHTRAG_VECTOR_STORAGE` | `ChromaVectorDBStorage` | Vector DB class |
| `LIGHTRAG_GRAPH_STORAGE` | `Neo4JStorage` | Graph storage class |
| `LIGHTRAG_DOC_STATUS_STORAGE` | `JsonDocStatusStorage` | Doc status storage class |
| `WORKSPACE` | `default` | Default tenant id when not passed per request |
| `WORKING_DIR` | `./rag_storage` | Base RAG working directory |

## Neo4j (when `LIGHTRAG_GRAPH_STORAGE=Neo4JStorage`)
| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `neo4j://localhost:7687` | Neo4j connection URI |
| `NEO4J_USERNAME` | `neo4j` | Username |
| `NEO4J_PASSWORD` | (empty) | Password |
| `NEO4J_DATABASE` | `neo4j` | Database name |

## Chroma (when `LIGHTRAG_VECTOR_STORAGE=ChromaVectorDBStorage`)
| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_HOST` | `localhost` | Chroma server host |
| `CHROMA_PORT` | `8000` | Chroma server port |

## RAGAnything / parser
| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `./output` | Parser output directory |
| `PARSE_METHOD` | `auto` | Parse method: auto, ocr, txt |
| `PARSER` | `mineru` | Parser: mineru, docling, paddleocr |
| `ENABLE_IMAGE_PROCESSING` | `true` | Enable image modal processing |
| `ENABLE_TABLE_PROCESSING` | `true` | Enable table modal processing |
| `ENABLE_EQUATION_PROCESSING` | `true` | Enable equation modal processing |

## LLM / Embedding
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_SERVICE_BASE_URL` | `http://localhost:8081` | Base URL of llm-service used for completions and embeddings (`/llm/complete`, `/llm/embeddings`) |
| `LLM_SERVICE_LLM_PROVIDER` | `openai` | Provider alias passed to llm-service (`openai`, `ollama`, etc.) |
| `LLM_SERVICE_EMBEDDING_PROVIDER` | same as LLM provider | Provider alias passed to llm-service for embeddings |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | Embedding model |
| `EMBEDDING_DIM` | `3072` | Embedding dimension |
| `LLM_BINDING_API_KEY` | (from `OPENAI_API_KEY`) | Legacy/compat setting (not required by doc-processing path) |
| `LLM_BINDING_HOST` | (from `OPENAI_BASE_URL`) | Legacy/compat setting (not required by doc-processing path) |
| `EMBEDDING_BINDING_HOST` | same as LLM | Legacy/compat embedding host (not required by doc-processing path) |
| `EMBEDDING_BINDING_API_KEY` | same as LLM | Legacy/compat embedding key (not required by doc-processing path) |

## LightRAG query/indexing (optional)
| Variable | Default | Description |
|----------|---------|-------------|
| `TOP_K` | `60` | Top-k retrieval |
| `CHUNK_TOP_K` | `20` | Chunk top-k |
| `MAX_ENTITY_TOKENS` | `6000` | Max entity tokens |
| `MAX_RELATION_TOKENS` | `8000` | Max relation tokens |
| `MAX_TOTAL_TOKENS` | `30000` | Max total context tokens |
| `COSINE_THRESHOLD` | `0.2` | Cosine similarity threshold |
