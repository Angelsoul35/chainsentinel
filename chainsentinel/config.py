"""Application configuration, loaded from environment variables (prefix ``CS_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CS_", env_file=".env", extra="ignore")

    environment: str = "local"
    model_dir: str = "artifacts"
    structuring_threshold: float = 10_000.0
    # Chosen by chainsentinel.evaluate.choose_threshold over four held-out
    # validation graphs (seeds 123, 321, 456, 654): the highest-precision operating
    # point whose recall stays >= 0.98 on the *worst* of them. In AML a missed
    # launderer is the expensive error, so recall is the binding constraint and
    # precision is maximised beneath it. The test graphs (777, 888, 999, 1234,
    # 2024) are never used for tuning, so their reported metrics measure generalisation, not fit.
    alert_threshold: float = 0.81
    report_mode: str = "template"  # template | llm
    llm_providers: str = "anthropic,openai,gemini,deepseek,ollama"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
