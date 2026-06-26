"""Shared in-memory RAG instance cache and factory."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import (
    WORKING_DIR,
    OUTPUT_DIR,
    PARSE_METHOD,
    PARSER,
    ENABLE_IMAGE_PROCESSING,
    ENABLE_TABLE_PROCESSING,
    ENABLE_EQUATION_PROCESSING,
    get_lightrag_kwargs,
    LLM_SERVICE_BASE_URL,
    LLM_SERVICE_LLM_PROVIDER,
    LLM_SERVICE_EMBEDDING_PROVIDER,
    LLM_MODEL,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
)
from app import db_config
from app.llm_client import DocProcessingLLMClient

if TYPE_CHECKING:
    from raganything import RAGAnything

_rag_cache: dict[str, "RAGAnything"] = {}
_CONFIG_KEYS = {"working_dir", "parser", "parse_method", "enable_image_processing", "enable_table_processing", "enable_equation_processing"}


def _get_rag(workspace: str, db_overrides: dict | None = None) -> "RAGAnything":
    """Build RAGAnything for workspace. db_overrides from DB are merged over env defaults."""
    from lightrag.utils import EmbeddingFunc
    from raganything import RAGAnything, RAGAnythingConfig

    if not LLM_SERVICE_BASE_URL:
        raise ValueError(
            "Set LLM_SERVICE_BASE_URL for LLM completions via llm-service."
        )

    lightrag_kwargs = get_lightrag_kwargs(workspace)
    working_dir = WORKING_DIR
    parser = PARSER
    parse_method = PARSE_METHOD
    enable_image = ENABLE_IMAGE_PROCESSING
    enable_table = ENABLE_TABLE_PROCESSING
    enable_equation = ENABLE_EQUATION_PROCESSING
    if db_overrides:
        for k, v in db_overrides.items():
            if k in lightrag_kwargs:
                lightrag_kwargs[k] = v
            if k in _CONFIG_KEYS:
                if k == "working_dir":
                    working_dir = v
                elif k == "parser":
                    parser = v
                elif k == "parse_method":
                    parse_method = v
                elif k == "enable_image_processing":
                    enable_image = v
                elif k == "enable_table_processing":
                    enable_table = v
                elif k == "enable_equation_processing":
                    enable_equation = v
    lightrag_kwargs["working_dir"] = working_dir
    lightrag_kwargs["workspace"] = workspace

    config = RAGAnythingConfig(
        working_dir=working_dir,
        parser=parser,
        parse_method=parse_method,
        enable_image_processing=enable_image,
        enable_table_processing=enable_table,
        enable_equation_processing=enable_equation,
    )

    llm_client = DocProcessingLLMClient(
        base_url=LLM_SERVICE_BASE_URL,
        provider=LLM_SERVICE_LLM_PROVIDER,
        model=LLM_MODEL,
    )
    embedding_client = DocProcessingLLMClient(
        base_url=LLM_SERVICE_BASE_URL,
        provider=LLM_SERVICE_EMBEDDING_PROVIDER,
        model=EMBEDDING_MODEL,
    )

    async def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        return await llm_client.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            model=kwargs.pop("model", None),
            reasoning_effort=kwargs.pop("reasoning_effort", None),
            response_format=kwargs.pop("response_format", None),
            **kwargs,
        )

    async def vision_model_func(
        prompt, system_prompt=None, history_messages=None, image_data=None, messages=None, **kwargs
    ):
        if messages:
            return await llm_client.complete(
                messages=messages,
                model=kwargs.pop("model", None),
                reasoning_effort=kwargs.pop("reasoning_effort", None),
                response_format=kwargs.pop("response_format", None),
                **kwargs,
            )
        if image_data:
            vision_messages = [
                {"role": "system", "content": system_prompt} if system_prompt else None,
                {
                    "role": "user",
                    "content": f"{prompt}\n\n[image_base64]\n{image_data}",
                },
            ]
            return await llm_client.complete(
                messages=[
                    m for m in vision_messages if m is not None
                ],
                model=kwargs.pop("model", None),
                reasoning_effort=kwargs.pop("reasoning_effort", None),
                response_format=kwargs.pop("response_format", None),
                **kwargs,
            )
        return await llm_model_func(prompt, system_prompt, history_messages or [], **kwargs)

    embedding_func = EmbeddingFunc(
        embedding_dim=EMBEDDING_DIM,
        max_token_size=8192,
        func=lambda texts: embedding_client.embeddings(
            input_texts=texts,
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIM,
        ),
    )

    return RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
        lightrag_kwargs=lightrag_kwargs,
    )


async def get_rag(workspace: str) -> "RAGAnything":
    """Return RAG for workspace; load config from DB if present, then build and cache."""
    if workspace in _rag_cache:
        return _rag_cache[workspace]
    db_overrides = await db_config.get_config(workspace) if db_config._pool else None
    _rag_cache[workspace] = _get_rag(workspace, db_overrides)
    return _rag_cache[workspace]


