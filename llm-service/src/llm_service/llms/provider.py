from __future__ import annotations

PROVIDER_ALIASES = frozenset({"groq", "openai", "anthropic", "ollama"})


def validate_provider(provider: str) -> str:
    """Return normalized provider alias or raise ``ValueError``."""
    prov = provider.strip().lower()
    if prov not in PROVIDER_ALIASES:
        allowed = ", ".join(sorted(PROVIDER_ALIASES))
        raise ValueError(f"Unknown provider {provider!r}. Expected one of: {allowed}.")
    return prov


def infer_provider(model: str) -> str:
    """Derive provider alias from a LiteLLM model id or bare model name (OpenAI-compat paths)."""
    name = model.strip()
    if not name:
        return "openai"
    if "/" in name:
        prefix = name.split("/", 1)[0].lower()
        if prefix in PROVIDER_ALIASES:
            return prefix
    lower = name.lower()
    if lower.startswith("gpt-") or lower.startswith("o1") or lower.startswith("text-embedding"):
        return "openai"
    if "claude" in lower:
        return "anthropic"
    if lower.startswith("llama") or lower.startswith("mixtral") or lower.startswith("gemma"):
        return "groq"
    return "openai"


def normalize_litellm_model(model: str, provider: str) -> str:
    """Map API ``(provider, model)`` to a LiteLLM model id.

    The request ``provider`` is authoritative for routing (Groq, OpenAI, etc.).

    - ``groq`` + ``openai/gpt-oss-120b`` → ``groq/openai/gpt-oss-120b`` (vendor path under Groq)
    - ``groq`` + ``meta-llama/llama-4-scout-17b-16e-instruct`` → ``groq/meta-llama/...``
    - ``groq`` + ``groq/llama-3.3-70b-versatile`` → unchanged (prefix already matches)
    - ``openai`` + ``gpt-4o-mini`` → ``openai/gpt-4o-mini``
    - ``anthropic`` + ``claude-3-5-sonnet-20241022`` → ``anthropic/claude-3-5-sonnet-20241022``
    - ``ollama`` + ``ibm/granite-docling:latest`` → ``ollama/ibm/granite-docling:latest``
    """
    name = model.strip()
    if not name:
        return name
    prov = validate_provider(provider)

    if "/" in name:
        prefix = name.split("/", 1)[0].lower()
        if prefix in PROVIDER_ALIASES and prefix == prov:
            return name
        return f"{prov}/{name}"

    return f"{prov}/{name}"
