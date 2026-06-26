from __future__ import annotations

import logging
from typing import Any

from llm_service.llms.config import get_default_model, get_fallback_model

logger = logging.getLogger(__name__)


def _supports_response_format(model: str) -> bool:
    try:
        import litellm

        params = litellm.get_supported_openai_params(model=model)
        return "response_format" in (params or [])
    except Exception:
        return False


def _supports_response_schema(model: str) -> bool:
    try:
        import litellm

        return bool(litellm.supports_response_schema(model=model))
    except Exception:
        return False


def _ensure_structured_output_supported(model: str, response_format: Any) -> None:
    if response_format is None:
        return
    if isinstance(response_format, dict):
        rf_type = str(response_format.get("type", "")).strip().lower()
        if rf_type == "json_object":
            if not _supports_response_format(model):
                raise ValueError(f"Model does not support response_format=json_object: {model}")
            return
        if rf_type == "json_schema":
            if not _supports_response_schema(model):
                raise ValueError(f"Model does not support response_format=json_schema: {model}")
            return
        raise ValueError("Invalid response_format. Expected type=json_object or type=json_schema.")
    if not _supports_response_schema(model):
        raise ValueError(f"Model does not support response schema output: {model}")


def _supports_reasoning(model: str) -> bool:
    try:
        import litellm

        return bool(litellm.supports_reasoning(model=model))
    except Exception:
        return False


def _ensure_reasoning_supported(model: str, reasoning_effort: Any) -> None:
    if reasoning_effort is None:
        return
    if reasoning_effort not in ("low", "medium", "high"):
        raise ValueError("Invalid reasoning_effort. Expected one of: low, medium, high.")
    if not _supports_reasoning(model):
        raise ValueError(f"Model does not support reasoning_effort: {model}")


def _apply_groq_rate_limit(model: str) -> None:
    from llm_service.llms.groq_ratelimit import get_groq_rate_limiter

    get_groq_rate_limiter().wait_if_needed(model)


def _record_groq_request(model: str) -> None:
    from llm_service.llms.groq_ratelimit import get_groq_rate_limiter

    get_groq_rate_limiter().record_request(model)


class LLMClient:
    def __init__(self, default_model: str | None = None, fallback_model: str | None = None):
        self._default_model = default_model or get_default_model()
        self._fallback_model = fallback_model or get_fallback_model()

    async def acomplete_with_fallback(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        *,
        route: str = "completion",
        **kwargs: Any,
    ) -> str:
        from litellm import acompletion

        model = model or self._default_model
        litellm_kwargs = {k: v for k, v in kwargs.items() if k != "route"}
        try:
            _ensure_reasoning_supported(model, litellm_kwargs.get("reasoning_effort"))
            _ensure_structured_output_supported(model, litellm_kwargs.get("response_format"))
            _apply_groq_rate_limit(model)
            logger.debug("%s litellm primary model=%s", route, model)
            response = await acompletion(model=model, messages=messages, **litellm_kwargs)
            _record_groq_request(model)
            return self._extract_content(response)
        except Exception as primary_err:
            logger.warning(
                "%s litellm primary failed model=%s: %s",
                route,
                model,
                primary_err,
                exc_info=True,
            )
            _ensure_reasoning_supported(self._fallback_model, litellm_kwargs.get("reasoning_effort"))
            _ensure_structured_output_supported(self._fallback_model, litellm_kwargs.get("response_format"))
            _apply_groq_rate_limit(self._fallback_model)
            logger.debug("%s litellm fallback model=%s", route, self._fallback_model)
            try:
                response = await acompletion(
                    model=self._fallback_model, messages=messages, **litellm_kwargs
                )
                _record_groq_request(self._fallback_model)
                return self._extract_content(response)
            except Exception as fallback_err:
                logger.error(
                    "%s litellm fallback failed model=%s: %s",
                    route,
                    self._fallback_model,
                    fallback_err,
                    exc_info=True,
                )
                raise fallback_err from primary_err

    @staticmethod
    def _extract_content(response: Any) -> str:
        if not response or not getattr(response, "choices", None):
            return ""
        msg = getattr(response.choices[0], "message", None)
        if not msg:
            return ""
        return getattr(msg, "content", "") or ""
