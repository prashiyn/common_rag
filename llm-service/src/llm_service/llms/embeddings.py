from __future__ import annotations

from typing import Any

import requests

from llm_service.config import get_settings


class EmbeddingClient:
    def __init__(self, default_model: str | None = None):
        self._default_model = default_model or "text-embedding-3-small"

    async def aembed(self, input_data: str | list[str], *, model: str | None = None, **kwargs: Any) -> dict[str, Any]:
        model_name = model or self._default_model
        if model_name.startswith("ollama/"):
            return self._embed_ollama(input_data, model_name)
        from litellm import aembedding

        return self._to_dict(await aembedding(model=model_name, input=input_data, **kwargs))

    def _embed_ollama(self, input_data: str | list[str], model: str) -> dict[str, Any]:
        base_url = get_settings().ollama_api_base.rstrip("/")
        model_name = model.split("/", 1)[1] if "/" in model else model
        r = requests.post(f"{base_url}/api/embed", json={"model": model_name, "input": input_data}, timeout=120)
        if r.status_code == 404:
            legacy_prompt = input_data[0] if isinstance(input_data, list) else input_data
            r = requests.post(f"{base_url}/api/embeddings", json={"model": model_name, "prompt": legacy_prompt}, timeout=120)
        r.raise_for_status()
        body = r.json()
        vectors = body.get("embeddings") if isinstance(body.get("embeddings"), list) else [body.get("embedding")]
        data = [{"object": "embedding", "index": i, "embedding": vec} for i, vec in enumerate(vectors) if vec is not None]
        return {"object": "list", "model": model, "data": data, "usage": body.get("usage")}

    @staticmethod
    def _to_dict(resp: Any) -> dict[str, Any]:
        if isinstance(resp, dict):
            return resp
        if hasattr(resp, "model_dump"):
            return resp.model_dump()
        if hasattr(resp, "dict"):
            return resp.dict()
        raise TypeError("Unsupported embedding response type")
