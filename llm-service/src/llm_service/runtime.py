"""Direct in-process LLM gateway calls (Phase 2 — unified API).

When ``LLM_CLIENT_MODE=inprocess`` or ``LLM_SERVICE_BASE_URL`` points at localhost,
consumers call ``run_completion`` / ``run_embeddings`` / ``get_models`` directly
instead of HTTP round-trips to the mounted ``/llm-service`` routes.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine
from typing import Any, Literal, TypeVar

from llm_service.llms.gateway import get_models, run_completion, run_embeddings
from llm_service.llms.models import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelsResponse,
)

ClientMode = Literal["http", "inprocess"]

_T = TypeVar("_T")

_LOCAL_INPROCESS_PREFIXES = ("http://localhost", "http://127.0.0.1")


def resolve_llm_client_mode(base_url: str | None = None) -> ClientMode:
    """Return ``inprocess`` for unified same-process calls, else ``http``."""
    explicit = os.getenv("LLM_CLIENT_MODE", "").strip().lower()
    if explicit == "http":
        return "http"
    if explicit == "inprocess":
        return "inprocess"
    url = (base_url or os.getenv("LLM_SERVICE_BASE_URL", "")).strip().lower()
    if any(url.startswith(prefix) for prefix in _LOCAL_INPROCESS_PREFIXES):
        return "inprocess"
    return "http"


def run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine from sync code (safe inside a running event loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def acomplete_dict(body: dict[str, Any]) -> dict[str, Any]:
    req = CompletionRequest.model_validate(body)
    resp: CompletionResponse = await run_completion(req, route="inprocess")
    return resp.model_dump()


async def aembeddings_dict(body: dict[str, Any]) -> dict[str, Any]:
    req = EmbeddingRequest.model_validate(body)
    resp: EmbeddingResponse = await run_embeddings(req)
    return resp.model_dump()


def models_dict() -> dict[str, Any]:
    resp: ModelsResponse = get_models()
    return resp.model_dump()


def complete_dict(body: dict[str, Any]) -> dict[str, Any]:
    return run_async(acomplete_dict(body))


def embeddings_dict(body: dict[str, Any]) -> dict[str, Any]:
    return run_async(aembeddings_dict(body))
