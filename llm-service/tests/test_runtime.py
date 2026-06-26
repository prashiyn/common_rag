from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from llm_service.llms.models import CompletionResponse, ModelsResponse
from llm_service.runtime import (
    acomplete_dict,
    complete_dict,
    models_dict,
    resolve_llm_client_mode,
)


@pytest.mark.parametrize(
    ("env", "base_url", "expected"),
    [
        ({"LLM_CLIENT_MODE": "inprocess"}, "http://remote:9000", "inprocess"),
        ({"LLM_CLIENT_MODE": "http"}, "http://localhost:8000/llm-service", "http"),
        ({}, "http://localhost:8000/llm-service", "inprocess"),
        ({}, "http://127.0.0.1:8000/llm-service", "inprocess"),
        ({}, "http://unified_api:8000/llm-service", "http"),
        ({}, "http://llm-service:8001", "http"),
    ],
)
def test_resolve_llm_client_mode(
    env: dict[str, str],
    base_url: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_CLIENT_MODE", raising=False)
    monkeypatch.delenv("LLM_SERVICE_BASE_URL", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert resolve_llm_client_mode(base_url) == expected


@pytest.mark.asyncio
async def test_acomplete_dict() -> None:
    with patch(
        "llm_service.runtime.run_completion",
        new_callable=AsyncMock,
        return_value=CompletionResponse(content="hello", parsed=None),
    ):
        out = await acomplete_dict(
            {"provider": "openai", "messages": [{"role": "user", "content": "hi"}]}
        )
    assert out == {"content": "hello", "parsed": None}


def test_complete_dict_sync() -> None:
    with patch(
        "llm_service.runtime.run_completion",
        new_callable=AsyncMock,
        return_value=CompletionResponse(content="sync", parsed=None),
    ):
        out = complete_dict(
            {"provider": "openai", "messages": [{"role": "user", "content": "hi"}]}
        )
    assert out["content"] == "sync"


def test_models_dict() -> None:
    with patch(
        "llm_service.runtime.get_models",
        return_value=ModelsResponse(
            default_model="a",
            fallback_model="b",
            models=["a", "b"],
        ),
    ):
        out = models_dict()
    assert out["default_model"] == "a"
    assert out["models"] == ["a", "b"]
