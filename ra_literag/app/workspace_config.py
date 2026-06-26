"""
Workspace config schema: allowed keys, validation, and merge-with-defaults for POST /config/{workspace_id}.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.config import (
    CHROMA_HOST,
    CHROMA_PORT,
    COSINE_THRESHOLD,
    ENABLE_EQUATION_PROCESSING,
    ENABLE_IMAGE_PROCESSING,
    ENABLE_TABLE_PROCESSING,
    LIGHTRAG_DOC_STATUS_STORAGE,
    LIGHTRAG_GRAPH_STORAGE,
    LIGHTRAG_KV_STORAGE,
    LIGHTRAG_VECTOR_STORAGE,
    MAX_ENTITY_TOKENS,
    MAX_RELATION_TOKENS,
    MAX_TOTAL_TOKENS,
    PARSE_METHOD,
    PARSER,
    TOP_K,
    CHUNK_TOP_K,
    WORKING_DIR,
)


PARSER_VALUES = frozenset({"mineru", "docling", "paddleocr"})
PARSE_METHOD_VALUES = frozenset({"auto", "ocr", "txt"})


class WorkspaceConfigPayload(BaseModel):
    """Allowed workspace config keys for POST /config/{workspace_id}. Extra keys are forbidden."""

    model_config = ConfigDict(extra="forbid")

    working_dir: str | None = None
    parser: str | None = None
    parse_method: str | None = None
    enable_image_processing: bool | None = None
    enable_table_processing: bool | None = None
    enable_equation_processing: bool | None = None
    kv_storage: str | None = None
    vector_storage: str | None = None
    graph_storage: str | None = None
    doc_status_storage: str | None = None
    top_k: int | None = None
    chunk_top_k: int | None = None
    max_entity_tokens: int | None = None
    max_relation_tokens: int | None = None
    max_total_tokens: int | None = None
    cosine_better_than_threshold: float | None = None
    vector_db_storage_cls_kwargs: dict[str, Any] | None = None

    @field_validator("parser")
    @classmethod
    def parser_allowed(cls, v: str | None) -> str | None:
        if v is not None and v not in PARSER_VALUES:
            raise ValueError(f"parser must be one of {sorted(PARSER_VALUES)}")
        return v

    @field_validator("parse_method")
    @classmethod
    def parse_method_allowed(cls, v: str | None) -> str | None:
        if v is not None and v not in PARSE_METHOD_VALUES:
            raise ValueError(f"parse_method must be one of {sorted(PARSE_METHOD_VALUES)}")
        return v

    @field_validator("top_k", "chunk_top_k", "max_entity_tokens", "max_relation_tokens", "max_total_tokens")
    @classmethod
    def positive_int(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("must be positive")
        return v

    @field_validator("cosine_better_than_threshold")
    @classmethod
    def cosine_range(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 1):
            raise ValueError("must be between 0 and 1")
        return v

    @field_validator("vector_db_storage_cls_kwargs")
    @classmethod
    def vector_kwargs_shape(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("must be a dict")
        allowed = {"host", "port"}
        if not set(v.keys()) <= allowed:
            raise ValueError(f"only keys {sorted(allowed)} allowed")
        if "host" in v and not isinstance(v["host"], str):
            raise ValueError("host must be str")
        if "port" in v and not isinstance(v["port"], int):
            raise ValueError("port must be int")
        return v


def get_default_workspace_config(workspace: str) -> dict[str, Any]:
    """Full config dict from env defaults for the given workspace (for merge and store)."""
    from app.config import get_lightrag_kwargs

    base = get_lightrag_kwargs(workspace)
    base["parser"] = PARSER
    base["parse_method"] = PARSE_METHOD
    base["enable_image_processing"] = ENABLE_IMAGE_PROCESSING
    base["enable_table_processing"] = ENABLE_TABLE_PROCESSING
    base["enable_equation_processing"] = ENABLE_EQUATION_PROCESSING
    if "Chroma" in LIGHTRAG_VECTOR_STORAGE and "vector_db_storage_cls_kwargs" not in base:
        base["vector_db_storage_cls_kwargs"] = {"host": CHROMA_HOST, "port": CHROMA_PORT}
    base["workspace"] = workspace
    return base


def merge_workspace_config(workspace: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Merge partial payload with full default config. Returns complete config dict.
    Payload must already be validated (only known keys, correct types).
    """
    merged = get_default_workspace_config(workspace)
    for k, v in payload.items():
        if v is None:
            continue
        if k == "vector_db_storage_cls_kwargs" and isinstance(v, dict):
            merged[k] = {**(merged.get(k) or {}), **v}
        elif k in merged:
            merged[k] = v
    merged["workspace"] = workspace
    return merged
