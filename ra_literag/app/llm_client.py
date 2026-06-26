"""
Doc-processing backed LLM client.

All completion calls are proxied via doc-processing `/llm/complete` so this
service does not call provider LLM APIs directly for completions.
"""

from __future__ import annotations

from typing import Any

import httpx


class DocProcessingLLMError(RuntimeError):
    """Raised when doc-processing LLM completion fails."""


class DocProcessingLLMClient:
    """HTTP client for doc-processing LLM completion endpoint."""

    def __init__(
        self,
        *,
        base_url: str,
        provider: str,
        model: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required for DocProcessingLLMClient")
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def complete(
        self,
        *,
        prompt: str | None = None,
        system_prompt: str | None = None,
        history_messages: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        response_format: dict[str, Any] | None = None,
        **_: Any,
    ) -> str:
        """
        Request completion from doc-processing.

        Unknown kwargs are ignored to remain compatible with upstream LightRAG
        call sites that may pass provider-specific arguments.
        """
        resolved_messages = messages or self._build_messages(
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
        )

        payload: dict[str, Any] = {
            "provider": self.provider,
            "messages": resolved_messages,
        }
        if model or self.model:
            payload["model"] = model or self.model
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            from llm_service.runtime import acomplete_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self.base_url) == "inprocess":
                body = await acomplete_dict(payload)
                content = body.get("content")
                if not isinstance(content, str):
                    raise DocProcessingLLMError(
                        "llm-service response missing string `content`"
                    )
                return content
        except ImportError:
            pass

        url = f"{self.base_url}/llm/complete"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise DocProcessingLLMError(
                f"doc-processing request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            detail = response.text
            raise DocProcessingLLMError(
                f"doc-processing returned {response.status_code}: {detail}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise DocProcessingLLMError(
                "doc-processing returned non-JSON response"
            ) from exc

        content = body.get("content")
        if not isinstance(content, str):
            raise DocProcessingLLMError(
                "doc-processing response missing string `content`"
            )
        return content

    async def models(self) -> dict[str, Any]:
        """Fetch configured models from doc-processing."""
        try:
            from llm_service.runtime import models_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self.base_url) == "inprocess":
                return models_dict()
        except ImportError:
            pass

        url = f"{self.base_url}/llm/models"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise DocProcessingLLMError(
                f"doc-processing models request failed: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise DocProcessingLLMError(
                f"doc-processing models returned {response.status_code}: {response.text}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise DocProcessingLLMError(
                "doc-processing models returned non-JSON response"
            ) from exc
        if not isinstance(body, dict):
            raise DocProcessingLLMError("doc-processing models response must be an object")
        return body

    async def embeddings(
        self,
        *,
        input_texts: str | list[str],
        model: str | None = None,
        dimensions: int | None = None,
        encoding_format: str | None = None,
        input_type: str | None = None,
        user: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings via doc-processing `/llm/embeddings`."""
        payload: dict[str, Any] = {
            "provider": self.provider,
            "input": input_texts,
        }
        if model or self.model:
            payload["model"] = model or self.model
        if dimensions is not None:
            payload["dimensions"] = dimensions
        if encoding_format is not None:
            payload["encoding_format"] = encoding_format
        if input_type is not None:
            payload["input_type"] = input_type
        if user is not None:
            payload["user"] = user

        try:
            from llm_service.runtime import aembeddings_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self.base_url) == "inprocess":
                body = await aembeddings_dict(payload)
                data = body.get("data")
                if not isinstance(data, list):
                    raise DocProcessingLLMError(
                        "llm-service embeddings response missing list `data`"
                    )
                vectors: list[list[float]] = []
                for item in data:
                    if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                        raise DocProcessingLLMError(
                            "llm-service embeddings response has invalid `data[].embedding`"
                        )
                    vectors.append(item["embedding"])
                return vectors
        except ImportError:
            pass

        url = f"{self.base_url}/llm/embeddings"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise DocProcessingLLMError(
                f"doc-processing embeddings request failed: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise DocProcessingLLMError(
                f"doc-processing embeddings returned {response.status_code}: {response.text}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise DocProcessingLLMError(
                "doc-processing embeddings returned non-JSON response"
            ) from exc
        data = body.get("data")
        if not isinstance(data, list):
            raise DocProcessingLLMError(
                "doc-processing embeddings response missing list `data`"
            )
        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                raise DocProcessingLLMError(
                    "doc-processing embeddings response has invalid `data[].embedding`"
                )
            vectors.append(item["embedding"])
        return vectors

    @staticmethod
    def _build_messages(
        *,
        prompt: str | None,
        system_prompt: str | None,
        history_messages: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history_messages:
            for item in history_messages:
                role = item.get("role")
                content = item.get("content")
                if isinstance(role, str) and content is not None:
                    messages.append({"role": role, "content": content})
        if prompt is not None:
            messages.append({"role": "user", "content": prompt})
        if not messages:
            messages.append({"role": "user", "content": ""})
        return messages
