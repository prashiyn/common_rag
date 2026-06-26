"""
GLM-OCR–style document OCR via llm-service (`POST /llm/complete`).

Implements the same high-level contract as the upstream GlmOcr.parse() → markdown result,
without calling Ollama directly. Model/provider/timeouts come from `src/config/llm_config.yaml`
use case (default `ocr_glm`). API contract: `llm_service_openapi.json`.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default prompt from GLM-OCR PageLoaderConfig (config.py)
_DEFAULT_PROMPT = (
    "Recognize the text in the image and output in Markdown format. "
    "Preserve the original layout (headings/paragraphs/tables/formulas). "
    "Do not fabricate content that does not exist in the image."
)


@dataclass
class GlmOcrConfig:
    """Per-parser options; LLM routing is resolved via llm_config use_case."""
    use_case: str = "ocr_glm"
    request_timeout: int | None = None


def load_config(config_path: str | Path | None) -> GlmOcrConfig:
    """Load optional overrides from YAML (config/glm_ocr_ollama.yaml)."""
    cfg = GlmOcrConfig()
    if not config_path:
        return cfg
    path = Path(config_path)
    if not path.exists():
        return cfg
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        ocr = (data.get("pipeline") or {}).get("ocr_api") or {}
        if ocr.get("use_case") is not None:
            cfg.use_case = str(ocr["use_case"]).strip() or "ocr_glm"
        if ocr.get("request_timeout") is not None:
            cfg.request_timeout = int(ocr["request_timeout"])
    except Exception:
        pass
    return cfg


@dataclass
class PipelineResult:
    """Minimal result: markdown and optional json/original_images for compatibility."""
    markdown_result: str
    json_result: list[Any]
    original_images: list[str]

    def __post_init__(self) -> None:
        if self.json_result is None:
            self.json_result = []
        if self.original_images is None:
            self.original_images = []


def _mime_for_path(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


class GlmOcrClient:
    """
    Vision OCR through llm-service.

    Same usage as upstream: GlmOcr(config_path="...") then parse(path) or parse([paths]).
    Returns PipelineResult (with markdown_result) or list of PipelineResult for list input.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        use_case: str | None = None,
        model: str | None = None,
        request_timeout: int | None = None,
    ) -> None:
        self._config = load_config(config_path)
        if use_case is not None:
            self._config.use_case = use_case
        if request_timeout is not None:
            self._config.request_timeout = request_timeout
        self._model_override = model
        from doc_processing.llm_runtime import HttpLLMRuntime

        self._llm = HttpLLMRuntime()

    def _read_image_as_base64(self, path: str | Path) -> tuple[str, str]:
        """Return (base64 payload, mime type) for one image file."""
        p = Path(path)
        raw = p.read_bytes()
        return base64.b64encode(raw).decode("ascii"), _mime_for_path(p)

    def _request_one(self, b64_images: list[str], mime: str, prompt: str) -> str:
        from doc_processing.llm_runtime.vision_messages import build_vision_user_messages

        messages = build_vision_user_messages(prompt, b64_images, mime_type=mime)
        try:
            timeout = float(self._config.request_timeout) if self._config.request_timeout is not None else None
            return self._llm.complete_with_fallback(
                messages,
                use_case=self._config.use_case,
                model=self._model_override,
                timeout_seconds=timeout,
            )
        except Exception as e:
            logger.warning(
                "GLM-OCR llm-service request failed: %s (use_case=%s, model=%s)",
                e,
                self._config.use_case,
                self._model_override,
            )
            return ""

    def parse(
        self,
        images: str | list[str],
        prompt: str = _DEFAULT_PROMPT,
    ) -> PipelineResult | list[PipelineResult]:
        """
        Run OCR on one or more images (file paths) via llm-service.

        - Single path (str) → one request, returns one PipelineResult.
        - List of paths (e.g. PDF pages) → one request per page, markdown concatenated into
          one PipelineResult (avoids timeouts and yields partial output per page).
        """
        single = isinstance(images, str)
        paths = [images] if single else list(images)
        if not paths:
            return PipelineResult("", [], []) if single else []

        image_paths = [str(Path(p).resolve()) for p in paths]

        if len(paths) > 1:
            parts: list[str] = []
            for i, p in enumerate(paths):
                b64, mime = self._read_image_as_base64(p)
                page_text = self._request_one([b64], mime, prompt)
                if page_text:
                    parts.append(page_text)
                else:
                    logger.warning("Page %s returned empty OCR result.", i + 1)
            text = "\n\n".join(parts)
        else:
            b64, mime = self._read_image_as_base64(paths[0])
            text = self._request_one([b64], mime, prompt)

        result = PipelineResult(
            markdown_result=text,
            json_result=[],
            original_images=image_paths,
        )
        return result if single else [result]

    def close(self) -> None:
        """No-op for compatibility with upstream context manager."""
        pass

    def __enter__(self) -> GlmOcrClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
