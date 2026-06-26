"""
Application configuration loaded from environment variables.

Populate via .env (see env.example). Used to build RAGAnythingConfig and
LightRAG init kwargs (including storage backends and per-tenant workspace).
"""

from __future__ import annotations

import os
from typing import Any

# Load .env early when this module is imported (e.g. from main)
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=False)


def _env(key: str, default: str | None = None, typ: type = str) -> Any:
    raw = os.getenv(key, default)
    if raw is None:
        return None
    if typ is bool:
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if typ is int:
        return int(raw)
    return str(raw).strip()


# ---------------------------------------------------------------------------
# LightRAG storage selection (see https://github.com/HKUDS/LightRAG)
# ---------------------------------------------------------------------------
LIGHTRAG_KV_STORAGE = _env("LIGHTRAG_KV_STORAGE", "JsonKVStorage")
LIGHTRAG_VECTOR_STORAGE = _env("LIGHTRAG_VECTOR_STORAGE", "ChromaVectorDBStorage")
LIGHTRAG_GRAPH_STORAGE = _env("LIGHTRAG_GRAPH_STORAGE", "Neo4JStorage")
LIGHTRAG_DOC_STATUS_STORAGE = _env("LIGHTRAG_DOC_STATUS_STORAGE", "JsonDocStatusStorage")

# Default workspace when not provided per request (multi-tenant: pass workspace per API call)
WORKSPACE_DEFAULT = _env("WORKSPACE", "default")

# Base working directory for RAG; per-workspace isolation is via LightRAG workspace param
WORKING_DIR = _env("WORKING_DIR", "./rag_storage")

# ---------------------------------------------------------------------------
# Neo4j (for LIGHTRAG_GRAPH_STORAGE=Neo4JStorage)
# ---------------------------------------------------------------------------
NEO4J_URI = _env("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = _env("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD", "")
NEO4J_DATABASE = _env("NEO4J_DATABASE", "neo4j")

# ---------------------------------------------------------------------------
# Chroma (for LIGHTRAG_VECTOR_STORAGE=ChromaVectorDBStorage)
# Chroma Docker often listens on port 8000; set CHROMA_HOST if not localhost
# ---------------------------------------------------------------------------
CHROMA_HOST = _env("CHROMA_HOST", "localhost")
CHROMA_PORT = _env("CHROMA_PORT", "8000", int)

# ---------------------------------------------------------------------------
# RAGAnything / parser
# ---------------------------------------------------------------------------
OUTPUT_DIR = _env("OUTPUT_DIR", "./output")
PARSE_METHOD = _env("PARSE_METHOD", "auto")
PARSER = _env("PARSER", "mineru")
ENABLE_IMAGE_PROCESSING = _env("ENABLE_IMAGE_PROCESSING", "true", bool)
ENABLE_TABLE_PROCESSING = _env("ENABLE_TABLE_PROCESSING", "true", bool)
ENABLE_EQUATION_PROCESSING = _env("ENABLE_EQUATION_PROCESSING", "true", bool)

# ---------------------------------------------------------------------------
# LLM / Embedding (both via llm-service: /llm/complete, /llm/embeddings)
# ---------------------------------------------------------------------------
LLM_SERVICE_BASE_URL = _env("LLM_SERVICE_BASE_URL", "http://localhost:8081")
LLM_SERVICE_LLM_PROVIDER = _env("LLM_SERVICE_LLM_PROVIDER", "openai")
LLM_SERVICE_EMBEDDING_PROVIDER = _env(
    "LLM_SERVICE_EMBEDDING_PROVIDER", LLM_SERVICE_LLM_PROVIDER
)
LLM_MODEL = _env("LLM_MODEL", "gpt-4o-mini")

LLM_BINDING_API_KEY = _env("LLM_BINDING_API_KEY") or _env("OPENAI_API_KEY")
LLM_BINDING_HOST = _env("LLM_BINDING_HOST") or _env("OPENAI_BASE_URL")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIM = _env("EMBEDDING_DIM", "3072", int)
EMBEDDING_BINDING_HOST = _env("EMBEDDING_BINDING_HOST") or LLM_BINDING_HOST
EMBEDDING_BINDING_API_KEY = _env("EMBEDDING_BINDING_API_KEY") or LLM_BINDING_API_KEY

# ---------------------------------------------------------------------------
# Optional LightRAG query/indexing params (from env)
# ---------------------------------------------------------------------------
TOP_K = _env("TOP_K", "60", int)
CHUNK_TOP_K = _env("CHUNK_TOP_K", "20", int)
MAX_ENTITY_TOKENS = _env("MAX_ENTITY_TOKENS", "6000", int)
MAX_RELATION_TOKENS = _env("MAX_RELATION_TOKENS", "8000", int)
MAX_TOTAL_TOKENS = _env("MAX_TOTAL_TOKENS", "30000", int)


def _cosine_threshold() -> float:
    try:
        return float(os.getenv("COSINE_THRESHOLD", "0.2"))
    except ValueError:
        return 0.2


COSINE_THRESHOLD = _cosine_threshold()


# LightRAG storage classes often read connection params from os.environ; set defaults if missing
os.environ.setdefault("CHROMA_HOST", CHROMA_HOST)
os.environ.setdefault("CHROMA_PORT", str(CHROMA_PORT))
os.environ.setdefault("NEO4J_URI", NEO4J_URI)
os.environ.setdefault("NEO4J_USERNAME", NEO4J_USERNAME)
os.environ.setdefault("NEO4J_PASSWORD", NEO4J_PASSWORD)
os.environ.setdefault("NEO4J_DATABASE", NEO4J_DATABASE)


def get_lightrag_kwargs(workspace: str) -> dict[str, Any]:
    """
    Build LightRAG init kwargs for the given workspace (tenant id).
    Data isolation is by workspace; pass workspace on every API request.
    """
    kwargs: dict[str, Any] = {
        "working_dir": WORKING_DIR,
        "workspace": workspace,
        "kv_storage": LIGHTRAG_KV_STORAGE,
        "vector_storage": LIGHTRAG_VECTOR_STORAGE,
        "graph_storage": LIGHTRAG_GRAPH_STORAGE,
        "doc_status_storage": LIGHTRAG_DOC_STATUS_STORAGE,
        "top_k": TOP_K,
        "chunk_top_k": CHUNK_TOP_K,
        "max_entity_tokens": MAX_ENTITY_TOKENS,
        "max_relation_tokens": MAX_RELATION_TOKENS,
        "max_total_tokens": MAX_TOTAL_TOKENS,
        "cosine_better_than_threshold": COSINE_THRESHOLD,
    }
    # Chroma: many LightRAG/Chroma integrations expect host/port in vector_db_storage_cls_kwargs
    if "Chroma" in LIGHTRAG_VECTOR_STORAGE:
        kwargs["vector_db_storage_cls_kwargs"] = {
            "host": CHROMA_HOST,
            "port": CHROMA_PORT,
        }
    return kwargs
