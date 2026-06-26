"""Thin HTTP client for llm-service (contract: llm_service_openapi.json at repo root)."""

from __future__ import annotations

from typing import Any

import requests

from doc_processing.config import get_settings
from doc_processing.debug_trace import debug_print
from doc_processing.llm_runtime.config import get_service_llm_runtime_config


class LlmServiceClient:
    """
    Typed paths and JSON bodies for the standalone llm-service.

    OpenAPI contract: `llm_service_openapi.json` (POST /llm/complete, GET /llm/models,
    POST /llm/embeddings).
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        default_timeout: float | None = None,
        service_auth_token: str | None = None,
    ) -> None:
        settings = get_settings()
        service_cfg = get_service_llm_runtime_config()
        cfg_timeout = service_cfg.get("timeout_seconds")
        resolved_url = (base_url or settings.llm_service_base_url).rstrip("/")
        if default_timeout is not None:
            resolved_timeout = float(default_timeout)
        elif isinstance(cfg_timeout, (int, float)):
            resolved_timeout = float(cfg_timeout)
        else:
            resolved_timeout = 120.0
        self._base_url = resolved_url
        self._default_timeout = resolved_timeout
        self._token = service_auth_token if service_auth_token is not None else settings.service_auth_token

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["X-Service-Token"] = self._token
        return headers

    def complete(
        self,
        body: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """POST /llm/complete — body matches `CompletionRequest` in llm_service_openapi.json."""
        try:
            from llm_service.runtime import complete_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self._base_url) == "inprocess":
                debug_print(
                    f"inprocess llm/complete model={body.get('model')} provider={body.get('provider')}"
                )
                return complete_dict(body)
        except ImportError:
            pass

        t = float(timeout) if timeout is not None else self._default_timeout
        try:
            debug_print(f"POST {self._base_url}/llm/complete model={body.get('model')} provider={body.get('provider')}")
            r = requests.post(
                f"{self._base_url}/llm/complete",
                json=body,
                headers=self._headers(),
                timeout=t,
            )
            if not r.ok:
                debug_print(f"llm/complete HTTP {r.status_code}: {r.text[:500]}")
            r.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"llm-service completion call failed: {e}") from e
        out = r.json()
        if not isinstance(out, dict):
            raise RuntimeError("Invalid completion response from llm-service: expected JSON object")
        return out

    def models(self) -> dict[str, Any]:
        """GET /llm/models — response matches `ModelsResponse` in llm_service_openapi.json."""
        try:
            from llm_service.runtime import models_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self._base_url) == "inprocess":
                return models_dict()
        except ImportError:
            pass

        try:
            r = requests.get(
                f"{self._base_url}/llm/models",
                headers=self._headers(),
                timeout=self._default_timeout,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"llm-service models call failed: {e}") from e
        out = r.json()
        if not isinstance(out, dict):
            raise RuntimeError("Invalid models response from llm-service")
        return out

    def embeddings(
        self,
        body: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """POST /llm/embeddings — body matches `EmbeddingRequest` in llm_service_openapi.json."""
        try:
            from llm_service.runtime import embeddings_dict, resolve_llm_client_mode

            if resolve_llm_client_mode(self._base_url) == "inprocess":
                return embeddings_dict(body)
        except ImportError:
            pass

        t = float(timeout) if timeout is not None else self._default_timeout
        try:
            r = requests.post(
                f"{self._base_url}/llm/embeddings",
                json=body,
                headers=self._headers(),
                timeout=t,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"llm-service embeddings call failed: {e}") from e
        out = r.json()
        if not isinstance(out, dict):
            raise RuntimeError("Invalid embeddings response from llm-service")
        return out
