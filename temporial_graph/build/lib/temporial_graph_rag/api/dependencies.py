from __future__ import annotations

from fastapi import HTTPException, Request

from temporial_graph_rag.graph import Neo4jGraphStore
from temporial_graph_rag.llm import LLMClient, LLMServiceConfig
from temporial_graph_rag.pipeline import ChunkProcessor


def get_neo4j_store(request: Request) -> Neo4jGraphStore | None:
    return getattr(request.app.state, "neo4j_store", None)


def get_chunk_processor() -> ChunkProcessor:
    config = LLMServiceConfig.from_env()
    client = LLMClient(config)
    return ChunkProcessor(client)


def get_llm_client() -> LLMClient:
    return LLMClient(LLMServiceConfig.from_env())


def require_neo4j_store(request: Request) -> Neo4jGraphStore:
    store = get_neo4j_store(request)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j is disabled. Set NEO4J_ENABLED=true and configure NEO4J_* in .env.",
        )
    return store
