"""Settings and config directory resolution for llm-service."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv_files() -> None:
    """Populate os.environ from dotfiles before ``Settings()`` is built."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    cwd = Path.cwd()
    # Repo-root .env first; cwd .env may override for local runs
    root_env = _PACKAGE_ROOT / ".env"
    if root_env.is_file():
        load_dotenv(root_env, override=False)
    cwd_env = cwd / ".env"
    if cwd_env.is_file():
        load_dotenv(cwd_env, override=True)

    for rel in ("src/config", "config"):
        keys = cwd / rel / "api_keys.env"
        if keys.is_file():
            load_dotenv(keys, override=False)


_load_dotenv_files()


class Settings(BaseSettings):
    # Environment variables are loaded by ``_load_dotenv_files()`` and the process environment.
    model_config = SettingsConfigDict(extra="ignore")

    # Service
    app_name: str = Field(default="llm-service", validation_alias="APP_NAME")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    litellm_debug: bool = Field(default=False, validation_alias="LITELLM_DEBUG")
    config_dir: str | None = Field(default=None, validation_alias="CONFIG_DIR")
    service_auth_token: str | None = Field(default=None, validation_alias="SERVICE_AUTH_TOKEN")

    # Groq (rate limits + API)
    groq_plan: Literal["FREE", "DEV"] = Field(default="FREE", validation_alias="GROQ_PLAN")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")

    # LLM providers (LiteLLM reads these from os.environ)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # Ollama (LiteLLM reads OLLAMA_API_BASE; also used for direct embedding HTTP)
    ollama_api_base: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_API_BASE")

    @field_validator("groq_plan", mode="before")
    @classmethod
    def _normalize_groq_plan(cls, v: object) -> object:
        if isinstance(v, str):
            u = v.strip().upper()
            return u if u in ("FREE", "DEV") else v
        return v

    @field_validator("litellm_debug", "debug", mode="before")
    @classmethod
    def _coerce_bool(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return v


def apply_litellm_env(settings: Settings) -> None:
    """Copy non-empty provider settings into ``os.environ`` so LiteLLM resolves API keys."""
    pairs: list[tuple[str, str | None]] = [
        ("GROQ_API_KEY", settings.groq_api_key),
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("OLLAMA_API_BASE", settings.ollama_api_base),
    ]
    for key, value in pairs:
        if value:
            os.environ[key] = value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_config_dir() -> Path:
    s = get_settings()
    if s.config_dir:
        return Path(s.config_dir).resolve()
    cwd = Path.cwd()
    for candidate in (cwd / "src" / "config", cwd / "config"):
        if candidate.is_dir():
            return candidate.resolve()
    return (cwd / "config").resolve()
