from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Reference-Aware Query Engine"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "change-me"
    neo4j_database: str = "neo4j"
    collection_aliases: str = "ril:RELIANCE,reliance:RELIANCE,infy:INFY,infosys:INFY"
    llm_service_base_url: str | None = None
    llm_processing_timeout_seconds: int = 15
    llm_config_path: str = "llm_config.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
