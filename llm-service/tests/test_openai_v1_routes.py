from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_v1_chat_completions_success_mocked(client: TestClient) -> None:
    mock_llm = MagicMock()
    mock_llm.acomplete_with_fallback = AsyncMock(return_value="hello from assistant")
    with patch("llm_service.llms.gateway._client", return_value=mock_llm):
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "hello from assistant"
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["id"].startswith("chatcmpl-")


def test_v1_chat_completions_rejects_stream(client: TestClient) -> None:
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "ping"}],
            "stream": True,
        },
    )
    assert r.status_code == 400
    assert "stream" in r.json()["detail"].lower()


def test_v1_models_lists_openai_shape(client: TestClient) -> None:
    r = client.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert isinstance(body["data"], list)
    if body["data"]:
        assert body["data"][0]["object"] == "model"
        assert "id" in body["data"][0]
        assert "owned_by" in body["data"][0]


def test_v1_embeddings_success_mocked(client: TestClient) -> None:
    mock_embed = MagicMock()
    mock_embed.aembed = AsyncMock(
        return_value={
            "object": "list",
            "model": "openai/text-embedding-3-small",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}],
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
    )
    with patch("llm_service.llms.gateway._embeddings_client", return_value=mock_embed):
        r = client.post(
            "/v1/embeddings",
            json={"model": "text-embedding-3-small", "input": ["hello"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert body["data"][0]["object"] == "embedding"
    assert body["data"][0]["embedding"] == [0.1, 0.2]
