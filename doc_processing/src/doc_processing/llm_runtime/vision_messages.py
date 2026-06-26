"""Vision user messages for llm-service ``POST /llm/complete``.

``CompletionRequest`` in ``llm_service_openapi.json`` requires each message field
(including ``content``) to be a string — not an OpenAI multimodal part array.
Images are inlined as data URLs in the user text; llm-service/LiteLLM maps them
for vision models.
"""

from __future__ import annotations

from typing import Any


def build_vision_user_messages(
    prompt: str,
    images_b64: list[str],
    *,
    mime_type: str = "image/png",
) -> list[dict[str, Any]]:
    """One user turn: ``prompt`` plus inline ``data:{mime};base64,...`` image(s)."""
    if not images_b64:
        return [{"role": "user", "content": prompt}]

    parts: list[str] = [prompt.strip()]
    for b64 in images_b64:
        parts.append(f"data:{mime_type};base64,{b64}")
    return [{"role": "user", "content": "\n\n".join(parts)}]
