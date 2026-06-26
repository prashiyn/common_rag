from __future__ import annotations

from typing import Any

import yaml

from llm_service.config import get_config_dir


def get_llm_config() -> dict[str, Any]:
    path = get_config_dir() / "llms.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def get_default_model() -> str:
    return str(get_llm_config().get("default_model", "gpt-4o-mini"))


def get_fallback_model() -> str:
    return str(get_llm_config().get("fallback_model", "gpt-3.5-turbo"))
