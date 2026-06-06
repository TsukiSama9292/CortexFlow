"""Application settings via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全域設定，從環境變數 / .env 載入。."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── LLM ───
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""  # optional, for proxy/compatible APIs

    # ─── Reddit ───
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    # ─── GitHub ───
    github_token: str = ""

    # ─── Pipeline ───
    relevance_threshold: int = 5
    max_results_per_source: int = 20
    request_timeout: int = 30


settings = Settings()
