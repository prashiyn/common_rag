"""Phase 2 — in-process LLM client integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://localhost:8000/llm-service", "inprocess"),
        ("http://unified_api:8000/llm-service", "http"),
    ],
)
def test_resolve_llm_client_mode(base_url: str, expected: str) -> None:
    from llm_service.runtime import resolve_llm_client_mode

    assert resolve_llm_client_mode(base_url) == expected


def test_doc_processing_client_inprocess_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_CLIENT_MODE", "inprocess")

    from doc_processing.llm_runtime.llm_service_client import LlmServiceClient

    with patch("llm_service.runtime.complete_dict", return_value={"content": "ok"}) as mock_ip:
        with patch("doc_processing.llm_runtime.llm_service_client.requests.post") as mock_http:
            out = LlmServiceClient(base_url="http://localhost:8000/llm-service").complete(
                {"provider": "openai", "messages": [{"role": "user", "content": "hi"}]}
            )
    assert out["content"] == "ok"
    mock_ip.assert_called_once()
    mock_http.assert_not_called()


@pytest.mark.asyncio
async def test_ra_literag_client_inprocess_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_CLIENT_MODE", "inprocess")

    from app.llm_client import DocProcessingLLMClient

    with patch(
        "llm_service.runtime.acomplete_dict",
        new_callable=AsyncMock,
        return_value={"content": "async-ok"},
    ) as mock_ip:
        with patch("httpx.AsyncClient.post") as mock_http:
            client = DocProcessingLLMClient(
                base_url="http://localhost:8000/llm-service",
                provider="openai",
            )
            text = await client.complete(prompt="hello")
    assert text == "async-ok"
    mock_ip.assert_awaited_once()
    mock_http.assert_not_called()


def test_temporial_graph_client_inprocess_skips_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_CLIENT_MODE", "inprocess")

    from temporial_graph_rag.llm.client import LLMClient
    from temporial_graph_rag.llm.config import LLMServiceConfig

    cfg = LLMServiceConfig(
        base_url="http://localhost:8000/llm-service",
        timeout_seconds=30,
        max_retries=0,
        retry_base_delay_ms=100,
        retry_max_delay_ms=1000,
        auth_mode="none",
        auth_token=None,
        tasks=LLMServiceConfig.default_tasks(),
    )
    client = LLMClient(cfg)
    try:
        with patch(
            "llm_service.runtime.models_dict",
            return_value={"default_model": "a", "fallback_model": "b", "models": ["a"]},
        ) as mock_ip:
            with patch.object(client._client, "request") as mock_http:
                out = client.models()
        assert out["default_model"] == "a"
        mock_ip.assert_called_once()
        mock_http.assert_not_called()
    finally:
        client.close()
