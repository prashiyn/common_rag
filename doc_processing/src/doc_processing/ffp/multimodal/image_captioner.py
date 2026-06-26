from __future__ import annotations

"""
Figure captioning for financial filing chunking.

Only charts/diagrams with readable financial data produce text; logos, photos,
and decorative images are discarded (``None``).
"""

from pathlib import Path

import base64

from doc_processing.llm_runtime import HttpLLMRuntime
from doc_processing.llm_runtime.vision_messages import build_vision_user_messages
from doc_processing.ffp.multimodal.llm_response import parse_relevance_response

_IMAGE_SYSTEM_PROMPT = """You analyze images from financial/regulatory filings.

Output strict JSON only — no markdown fences, no preamble:
{"relevant":false}
or
{"relevant":true,"text":"<summary>"}

Set relevant=false for: logos, brand marks, photos, icons, signatures, seals,
decorative graphics, blank or illegible images, or any image without readable
financial/numeric data.

Set relevant=true only for charts, graphs, or diagrams where specific metrics,
labels, or trends are visible. The text field must be 1–4 short sentences citing
only what is visible. No invented numbers.

Never output: generic chart-reading advice, numbered how-to lists, apologies,
requests for more context, or speculation when data is missing — use relevant=false instead."""

_JSON_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}


class ImageCaptioner:
    """Caption financially meaningful figures; skip irrelevant images."""

    def __init__(self, client: HttpLLMRuntime | None = None) -> None:
        self._client = client or HttpLLMRuntime()

    @staticmethod
    def _encode_image(path: str | Path) -> str:
        p_str = str(path)
        if p_str.startswith("http://") or p_str.startswith("https://"):
            import requests

            r = requests.get(p_str, timeout=30)
            r.raise_for_status()
            return base64.b64encode(r.content).decode("ascii")
        return base64.b64encode(Path(path).read_bytes()).decode("ascii")

    def caption(self, img_path: str | Path) -> str | None:
        """Return a short caption, or ``None`` if the image should be omitted from chunks."""
        image_b64 = self._encode_image(img_path)
        messages = [
            {"role": "system", "content": _IMAGE_SYSTEM_PROMPT},
            *build_vision_user_messages("Classify and summarize this image.", [image_b64]),
        ]

        try:
            raw = self._client.complete_with_fallback(
                messages,
                use_case="chunk_image_caption",
                response_format=_JSON_RESPONSE_FORMAT,
            )
        except Exception:
            raw = self._client.complete_with_fallback(
                messages,
                use_case="chunk_image_caption",
            )

        return parse_relevance_response(raw or "")
