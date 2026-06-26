from __future__ import annotations

"""Remote runtime client for doc-processing -> llm-service API calls."""

from typing import Any

from doc_processing.config import get_settings
from doc_processing.debug_trace import debug_print
from doc_processing.llm_runtime.config import get_service_llm_runtime_config, get_use_case_llm_config
from doc_processing.llm_runtime.llm_service_client import LlmServiceClient


_KNOWN_PROVIDER_PREFIXES = frozenset({"groq", "openai", "ollama", "anthropic"})


def _provider_from_model(model: str | None) -> str:
    if not model:
        return "openai"
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai"


def _normalize_service_model(provider: str, model: str | None) -> str | None:
    """Prefix model with provider for LiteLLM routing (llm-service may forward model only)."""
    if not model:
        return None
    p = provider.strip().lower()
    m = model.strip()
    if "/" in m and m.split("/", 1)[0].lower() == p:
        return m
    return f"{p}/{m}"


class HttpLLMRuntime:
    """
    Compatibility wrapper for LLM operations over standalone llm-service APIs.

    It supports use-case driven model/provider selection via `src/config/llm_config.yaml`,
    while allowing explicit per-call model overrides. Contract: `llm_service_openapi.json`.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        service_auth_token: str | None = None,
    ) -> None:
        settings = get_settings()
        service_cfg = get_service_llm_runtime_config()

        cfg_timeout = service_cfg.get("timeout_seconds")

        resolved_url = (base_url or settings.llm_service_base_url).rstrip("/")
        resolved_timeout = timeout_seconds
        if resolved_timeout is None:
            if isinstance(cfg_timeout, (int, float)):
                resolved_timeout = float(cfg_timeout)
            else:
                resolved_timeout = 120.0

        token = service_auth_token if service_auth_token is not None else settings.service_auth_token
        self._api = LlmServiceClient(
            base_url=resolved_url,
            default_timeout=float(resolved_timeout),
            service_auth_token=token,
        )
        self._default_timeout = float(resolved_timeout)

    @staticmethod
    def _resolve_provider_model(use_case: str | None, model: str | None) -> tuple[str, str | None]:
        case_cfg = get_use_case_llm_config(use_case)
        case_provider = (
            str(case_cfg.get("provider")).strip().lower() if case_cfg.get("provider") else None
        )
        resolved_model = model or (str(case_cfg.get("model")) if case_cfg.get("model") else None)

        if model and "/" in model:
            prefix = model.split("/", 1)[0].lower()
            if prefix in _KNOWN_PROVIDER_PREFIXES:
                provider = prefix
            elif case_provider:
                provider = case_provider
            else:
                provider = _provider_from_model(resolved_model)
        elif case_provider:
            provider = case_provider
        elif resolved_model:
            provider = _provider_from_model(resolved_model)
        else:
            provider = "openai"

        resolved_model = _normalize_service_model(provider, resolved_model)
        return provider, resolved_model

    @staticmethod
    def _request_timeout(
        use_case: str | None,
        *,
        call_timeout: float | None,
        default_timeout: float,
    ) -> float:
        if call_timeout is not None:
            return float(call_timeout)
        case_cfg = get_use_case_llm_config(use_case)
        ts = case_cfg.get("timeout_seconds")
        if isinstance(ts, (int, float)):
            return float(ts)
        return default_timeout

    def complete_with_fallback(
        self,
        messages: list[dict[str, Any]],
        *,
        use_case: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        response_format: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        provider, resolved_model = self._resolve_provider_model(use_case, model)
        case_cfg = get_use_case_llm_config(use_case)

        eff_reasoning = reasoning_effort
        if eff_reasoning is None:
            cr = case_cfg.get("reasoning_effort")
            if cr is not None:
                eff_reasoning = str(cr)

        eff_response_format = response_format
        if eff_response_format is None:
            rf = case_cfg.get("response_format")
            if isinstance(rf, dict):
                eff_response_format = rf

        payload: dict[str, Any] = {
            "provider": provider,
            "messages": messages,
            "model": resolved_model,
        }
        if eff_reasoning is not None:
            payload["reasoning_effort"] = eff_reasoning
        if eff_response_format is not None:
            payload["response_format"] = eff_response_format

        req_timeout = self._request_timeout(use_case, call_timeout=timeout_seconds, default_timeout=self._default_timeout)
        debug_print(
            "llm complete",
            f"use_case={use_case}",
            f"provider={provider}",
            f"model={resolved_model}",
            f"messages={len(messages)}",
        )
        body = self._api.complete(payload, timeout=req_timeout)
        debug_print("llm complete response keys:", list(body.keys()) if isinstance(body, dict) else type(body))
        content = body.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Invalid completion response from llm-service: missing string content")
        return content

    def embed(
        self,
        input_data: str | list[str],
        *,
        use_case: str | None = None,
        model: str | None = None,
        encoding_format: str | None = None,
        dimensions: int | None = None,
        input_type: str | None = None,
        user: str | None = None,
    ) -> dict[str, Any]:
        provider, resolved_model = self._resolve_provider_model(use_case, model)
        payload: dict[str, Any] = {
            "provider": provider,
            "input": input_data,
            "model": resolved_model,
        }
        if encoding_format is not None:
            payload["encoding_format"] = encoding_format
        if dimensions is not None:
            payload["dimensions"] = dimensions
        if input_type is not None:
            payload["input_type"] = input_type
        if user is not None:
            payload["user"] = user

        req_timeout = self._request_timeout(use_case, call_timeout=None, default_timeout=self._default_timeout)
        return self._api.embeddings(payload, timeout=req_timeout)
