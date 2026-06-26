from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from raqe.config import get_settings


@lru_cache(maxsize=1)
def load_llm_config() -> dict:
    settings = get_settings()
    config_path = Path(settings.llm_config_path)
    if not config_path.exists():
        return {"defaults": {"provider": "openai", "timeout_seconds": settings.llm_processing_timeout_seconds}, "use_cases": {}}
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    data.setdefault("defaults", {})
    data.setdefault("use_cases", {})
    return data


def get_use_case_config(use_case: str) -> dict:
    config = load_llm_config()
    defaults = config.get("defaults", {})
    use_case_config = config.get("use_cases", {}).get(use_case, {})
    merged = {**defaults, **use_case_config}
    return merged
