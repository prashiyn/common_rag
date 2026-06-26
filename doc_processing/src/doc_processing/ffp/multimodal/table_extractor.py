from __future__ import annotations

"""
Table-to-text conversion for financial filing chunking.

Only data tables with readable financial content produce text; non-tabular or
irrelevant images are discarded (``None``).
"""

from pathlib import Path

import base64

from doc_processing.llm_runtime import HttpLLMRuntime
from doc_processing.llm_runtime.vision_messages import build_vision_user_messages
from doc_processing.ffp.multimodal.llm_response import parse_relevance_response

_TABLE_SYSTEM_PROMPT = """You analyze table images from financial/regulatory filings.

Output strict JSON only — no markdown fences, no preamble:
{"relevant":false}
or
{"relevant":true,"text":"<summary>"}

Set relevant=false for: non-tabular images, logos, headers/footers only, decorative
layouts, blank or illegible crops, or tables without readable numeric/financial data.

Set relevant=true only when row/column financial data is visible. The text field must
be a concise factual summary (key line items, periods, and values shown). No invented
numbers.

Never output: generic advice on reading tables, numbered how-to lists, apologies,
requests for more context, or speculation — use relevant=false instead."""

_JSON_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}


class TableExtractor:
    """Convert financial data tables to text; skip non-tabular or empty tables."""

    def __init__(self, client: HttpLLMRuntime | None = None) -> None:
        self._client = client or HttpLLMRuntime()

    @staticmethod
    def _encode_image(path: str | Path) -> str:
        return base64.b64encode(Path(path).read_bytes()).decode("ascii")

    def convert(self, img_path: str | Path) -> str | None:
        """Return a short table summary, or ``None`` if the table should be omitted."""
        image_b64 = self._encode_image(img_path)
        messages = [
            {"role": "system", "content": _TABLE_SYSTEM_PROMPT},
            *build_vision_user_messages("Classify and summarize this table image.", [image_b64]),
        ]

        try:
            raw = self._client.complete_with_fallback(
                messages,
                use_case="chunk_table_extraction",
                response_format=_JSON_RESPONSE_FORMAT,
            )
        except Exception:
            raw = self._client.complete_with_fallback(
                messages,
                use_case="chunk_table_extraction",
            )

        return parse_relevance_response(raw or "")
