"""
Docling remote VLM wiring to Ollama (``VlmEngineType.API_OLLAMA``).

Docling calls Ollama's OpenAI-compatible chat API directly during conversion
(see Docling's vlm_pipeline_api_model example). FFP/OCR paths still use llm-service.
"""

from __future__ import annotations

from typing import Any

from docling.datamodel.pipeline_options import (
    PictureDescriptionVlmEngineOptions,
    VlmConvertOptions,
)
from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType

from doc_processing.config import get_settings
from doc_processing.debug_trace import debug_print
from doc_processing.llm_runtime.config import get_use_case_llm_config


def get_ollama_chat_completions_url() -> str:
    """``{OLLAMA_BASE_URL}/v1/chat/completions`` (default Ollama on port 11434)."""
    base = get_settings().ollama_base_url.rstrip("/")
    return f"{base}/v1/chat/completions"


def _resolve_timeout(use_case: str, override: float | None = None) -> float:
    if override is not None:
        return float(override)
    case_cfg = get_use_case_llm_config(use_case)
    ts = case_cfg.get("timeout_seconds")
    if isinstance(ts, (int, float)):
        return float(ts)
    return 120.0


def _ollama_native_model(use_case: str) -> str | None:
    """Map llm_config model (e.g. ``ollama/ibm/granite-docling:latest``) to Ollama model id."""
    case_cfg = get_use_case_llm_config(use_case)
    model = case_cfg.get("model")
    if not model:
        return None
    s = str(model).strip()
    if s.startswith("ollama/"):
        return s.split("/", 1)[1]
    return s


def _build_ollama_api_params(use_case: str) -> dict[str, Any]:
    case_cfg = get_use_case_llm_config(use_case)
    params: dict[str, Any] = {}
    api_params = case_cfg.get("api_params")
    if isinstance(api_params, dict):
        params.update(api_params)
    model = _ollama_native_model(use_case)
    if model:
        params["model"] = model
    return params


def build_ollama_vlm_engine_options(
    use_case: str,
    *,
    timeout: float | None = None,
) -> ApiVlmEngineOptions:
    """``ApiVlmEngineOptions`` for ``VlmEngineType.API_OLLAMA`` → local/docker Ollama."""
    params = _build_ollama_api_params(use_case)
    url = get_ollama_chat_completions_url()
    debug_print(f"docling Ollama VLM use_case={use_case} url={url} params={params}")
    return ApiVlmEngineOptions(
        engine_type=VlmEngineType.API_OLLAMA,
        url=url,
        params=params,
        timeout=_resolve_timeout(use_case, timeout),
    )


def build_vlm_convert_options(preset_id: str, use_case: str) -> VlmConvertOptions:
    """PDF VLM pipeline (e.g. preset ``granite_docling``) via Ollama."""
    return VlmConvertOptions.from_preset(
        preset_id,
        engine_options=build_ollama_vlm_engine_options(use_case),
    )


def build_picture_description_options(
    use_case: str,
    *,
    prompt: str | None = None,
) -> PictureDescriptionVlmEngineOptions:
    """In-pipeline picture captions via Ollama (preset ``granite_vision``)."""
    opts = PictureDescriptionVlmEngineOptions.from_preset(
        "granite_vision",
        engine_options=build_ollama_vlm_engine_options(use_case),
    )
    if prompt:
        opts.prompt = prompt
    if hasattr(opts, "picture_area_threshold"):
        opts.picture_area_threshold = 0.05
    return opts
