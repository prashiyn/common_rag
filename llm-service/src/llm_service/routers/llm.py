from __future__ import annotations

import logging

from fastapi import APIRouter

from llm_service.llms.gateway import get_models, run_completion, run_embeddings

logger = logging.getLogger(__name__)
from llm_service.llms.models import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsResponse,
)

router = APIRouter()


@router.post("/complete", response_model=CompletionResponse)
async def completion(req: CompletionRequest) -> CompletionResponse:
    logger.debug(
        "POST /llm/complete provider=%s model=%s messages=%d",
        req.provider,
        req.model,
        len(req.messages),
    )
    return await run_completion(req, route="POST /llm/complete")


@router.get("/models", response_model=ModelsResponse)
async def models() -> ModelsResponse:
    return get_models()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(req: EmbeddingRequest) -> EmbeddingResponse:
    return await run_embeddings(req)
