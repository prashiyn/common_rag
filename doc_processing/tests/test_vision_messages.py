from __future__ import annotations

from doc_processing.llm_runtime.vision_messages import build_vision_user_messages


def test_build_vision_user_messages_string_content() -> None:
    msgs = build_vision_user_messages("Describe this.", ["abc123"], mime_type="image/png")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    assert isinstance(content, str)
    assert "Describe this." in content
    assert "data:image/png;base64,abc123" in content
    assert not isinstance(content, list)
