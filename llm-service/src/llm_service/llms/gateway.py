from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

from llm_service.llms.client import LLMClient
from llm_service.llms.config import get_llm_config
from llm_service.llms.embeddings import EmbeddingClient
from llm_service.llms.provider import normalize_litellm_model, validate_provider
from llm_service.llms.models import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingDataItem,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsResponse,
    ResponseFormatJsonObject,
    ResponseFormatJsonSchema,
)

_llm_client: LLMClient | None = None
_embedding_client: EmbeddingClient | None = None


def _client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def _embeddings_client() -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


def _response_format_dump(
    response_format: ResponseFormatJsonObject | ResponseFormatJsonSchema | None,
) -> dict[str, Any] | None:
    if response_format is None:
        return None
    return response_format.model_dump(by_alias=True)


def _resolve_litellm_model(provider: str, model: str | None) -> str | None:
    if not model:
        return model
    validate_provider(provider)
    litellm_model = normalize_litellm_model(model, provider)
    return litellm_model


async def run_completion(req: CompletionRequest, *, route: str = "completion") -> CompletionResponse:
    try:
        litellm_model = _resolve_litellm_model(req.provider, req.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    logger.debug(
        "%s start provider=%s model=%s litellm_model=%s message_count=%d reasoning_effort=%s response_format=%s",
        route,
        req.provider,
        req.model,
        litellm_model,
        len(req.messages),
        req.reasoning_effort,
        req.response_format.type if req.response_format else None,
    )
    try:
        content = await _client().acomplete_with_fallback(
            req.messages,
            model=litellm_model,
            reasoning_effort=req.reasoning_effort,
            response_format=_response_format_dump(req.response_format),
            route=route,
        )
        parsed: Any | None = None
        if req.response_format is not None:
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = None
        logger.debug("%s ok litellm_model=%s content_len=%d", route, litellm_model, len(content))
        return CompletionResponse(content=content, parsed=parsed)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "%s failed provider=%s model=%s error_type=%s",
            route,
            req.provider,
            req.model,
            type(e).__name__,
        )
        raise HTTPException(status_code=502, detail=str(e)) from e


def get_models() -> ModelsResponse:
    cfg = get_llm_config()
    return ModelsResponse(
        default_model=cfg.get("default_model", "gpt-4o-mini"),
        fallback_model=cfg.get("fallback_model", "gpt-3.5-turbo"),
        models=cfg.get("models", []),
    )


async def run_embeddings(req: EmbeddingRequest) -> EmbeddingResponse:
    try:
        litellm_model = _resolve_litellm_model(req.provider, req.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        result = await _embeddings_client().aembed(
            req.input,
            model=litellm_model,
            encoding_format=req.encoding_format,
            dimensions=req.dimensions,
            input_type=req.input_type,
            user=req.user,
        )
        return EmbeddingResponse(
            object=str(result.get("object", "list")),
            model=str(result.get("model", req.model or "")),
            data=[
                EmbeddingDataItem(
                    object=str(item.get("object", "embedding")),
                    index=int(item.get("index", idx)),
                    embedding=item.get("embedding"),
                )
                for idx, item in enumerate(result.get("data", []))
            ],
            usage=result.get("usage"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
