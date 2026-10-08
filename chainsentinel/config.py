"""Application configuration, loaded from environment variables (prefix ``CS_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CS_", env_file=".env", extra="ignore")

    environment: str = "local"
    model_dir: str = "artifacts"
    structuring_threshold: float = 10_000.0
    alert_threshold: float = 0.5
    report_mode: str = "template"  # template | llm
    llm_providers: str = "anthropic,openai,gemini,deepseek,ollama"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
