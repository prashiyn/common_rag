from __future__ import annotations

import pytest

from llm_service.llms.provider import (
    normalize_litellm_model,
    validate_provider,
)


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        # Groq: vendor paths and hosted OpenAI OSS ids
        ("groq", "meta-llama/llama-4-scout-17b-16e-instruct", "groq/meta-llama/llama-4-scout-17b-16e-instruct"),
        ("groq", "openai/gpt-oss-120b", "groq/openai/gpt-oss-120b"),
        ("groq", "groq/llama-3.3-70b-versatile", "groq/llama-3.3-70b-versatile"),
        ("groq", "groq/groq/compound", "groq/groq/compound"),
        ("groq", "llama-3.1-8b-instant", "groq/llama-3.1-8b-instant"),
        # OpenAI
        ("openai", "gpt-4o-mini", "openai/gpt-4o-mini"),
        ("openai", "openai/gpt-4o", "openai/gpt-4o"),
        ("openai", "o1-preview", "openai/o1-preview"),
        # Anthropic
        ("anthropic", "claude-3-5-sonnet-20241022", "anthropic/claude-3-5-sonnet-20241022"),
        ("anthropic", "anthropic/claude-3-haiku-20240307", "anthropic/claude-3-haiku-20240307"),
        # Ollama
        ("ollama", "ibm/granite-docling:latest", "ollama/ibm/granite-docling:latest"),
        ("ollama", "ollama/llama3.2", "ollama/llama3.2"),
        # Explicit provider overrides mismatched LiteLLM prefix
        ("groq", "openai/gpt-oss-20b", "groq/openai/gpt-oss-20b"),
        ("openai", "groq/llama-3.3-70b-versatile", "openai/groq/llama-3.3-70b-versatile"),
    ],
)
def test_normalize_litellm_model_across_providers(
    provider: str, model: str, expected: str
) -> None:
    assert normalize_litellm_model(model, provider) == expected


@pytest.mark.parametrize("provider", ["groq", "GROQ", " OpenAI ", "ANTHROPIC", "ollama"])
def test_validate_provider_accepts_aliases(provider: str) -> None:
    assert validate_provider(provider) == provider.strip().lower()


def test_validate_provider_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        validate_provider("azure")
