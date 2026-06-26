from __future__ import annotations

import os
from typing import Any

from app.llm_client import DocProcessingLLMClient


def build_doc_processing_llm_client() -> DocProcessingLLMClient:
    """Client for ``/llm/complete`` (and ``/llm/models``) with LLM provider + chat model."""
    return DocProcessingLLMClient(
        base_url=os.getenv("LLM_SERVICE_BASE_URL", "http://localhost:8081"),
        provider=os.getenv("LLM_SERVICE_LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )


def build_doc_processing_embedding_client() -> DocProcessingLLMClient:
    """Client for ``/llm/embeddings`` with embedding provider + embedding model."""
    llm_prov = os.getenv("LLM_SERVICE_LLM_PROVIDER", "openai")
    embed_prov = os.getenv("LLM_SERVICE_EMBEDDING_PROVIDER", llm_prov)
    return DocProcessingLLMClient(
        base_url=os.getenv("LLM_SERVICE_BASE_URL", "http://localhost:8081"),
        provider=embed_prov,
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
    )


def build_doc_processing_client() -> DocProcessingLLMClient:
    """Backward-compatible alias for :func:`build_doc_processing_llm_client`."""
    return build_doc_processing_llm_client()


async def completion_func(
    client: DocProcessingLLMClient,
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> str:
    return await client.complete(
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        model=kwargs.pop("model", None),
        reasoning_effort=kwargs.pop("reasoning_effort", None),
        response_format=kwargs.pop("response_format", None),
        **kwargs,
    )


async def vision_completion_func(
    client: DocProcessingLLMClient,
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    image_data: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> str:
    if messages:
        return await client.complete(
            messages=messages,
            model=kwargs.pop("model", None),
            reasoning_effort=kwargs.pop("reasoning_effort", None),
            response_format=kwargs.pop("response_format", None),
            **kwargs,
        )
    if image_data:
        payload_messages = [
            {"role": "system", "content": system_prompt} if system_prompt else None,
            {"role": "user", "content": f"{prompt}\n\n[image_base64]\n{image_data}"},
        ]
        return await client.complete(
            messages=[m for m in payload_messages if m is not None],
            model=kwargs.pop("model", None),
            reasoning_effort=kwargs.pop("reasoning_effort", None),
            response_format=kwargs.pop("response_format", None),
            **kwargs,
        )
    return await completion_func(
        client,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def embeddings_func(
    client: DocProcessingLLMClient,
    texts: list[str],
    *,
    model: str | None = None,
    dimensions: int | None = None,
    **kwargs: Any,
) -> list[list[float]]:
    return await client.embeddings(
        input_texts=texts,
        model=model,
        dimensions=dimensions,
        encoding_format=kwargs.pop("encoding_format", None),
        input_type=kwargs.pop("input_type", None),
        user=kwargs.pop("user", None),
    )
