"""Unified settings — all env vars used by the merged services."""
from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class UnifiedSettings(BaseSettings):
    """Reference for operators; each service still reads its own config at runtime."""

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # Shared Neo4j
    neo4j_uri: str = Field("bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", alias="NEO4J_USER")
    neo4j_username: str = Field("neo4j", alias="NEO4J_USERNAME")
    neo4j_password: str = Field("", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field("neo4j", alias="NEO4J_DATABASE")
    neo4j_enabled: bool = Field(True, alias="NEO4J_ENABLED")

    # Postgres
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_user: str = Field("postgres", alias="POSTGRES_USER")
    postgres_password: str = Field("", alias="POSTGRES_PASSWORD")
    postgres_database: str = Field("ra_literag", alias="POSTGRES_DATABASE")

    # Chroma
    chroma_host: str = Field("localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(8000, alias="CHROMA_PORT")

    # Ollama
    ollama_api_base: str = Field("http://localhost:11434", alias="OLLAMA_API_BASE")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")

    # LLM service (self-reference when unified)
    llm_service_base_url: str = Field("http://localhost:8001", alias="LLM_SERVICE_BASE_URL")

    # llm-service keys
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    groq_plan: str = Field("FREE", alias="GROQ_PLAN")
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    litellm_debug: bool = Field(False, alias="LITELLM_DEBUG")

    # core_rag_graph
    graph_backend: str = Field("networkx", alias="GRAPH_BACKEND")
    graph_dual_write: bool = Field(False, alias="GRAPH_DUAL_WRITE")

    # ra_literag
    lightrag_vector_storage: str = Field("ChromaVectorDBStorage", alias="LIGHTRAG_VECTOR_STORAGE")
    lightrag_graph_storage: str = Field("Neo4JStorage", alias="LIGHTRAG_GRAPH_STORAGE")

    # temporial_graph_openai
    job_backend: str = Field("memory", alias="JOB_BACKEND")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")

    debug: bool = Field(False, alias="DEBUG")


def get_settings() -> UnifiedSettings:
    return UnifiedSettings()
