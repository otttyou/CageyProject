"""Runtime configuration loaded from environment variables and .env files."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CageySettings(BaseSettings):
    """Settings for the Cagey CLI. Values are read from the environment or a .env file."""

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    default_model: str = Field("claude-opus-4-6", alias="CAGEY_MODEL")
    default_concurrency: int = Field(5, alias="CAGEY_CONCURRENCY")
    max_tokens_per_call: int = Field(2048, alias="CAGEY_MAX_TOKENS")
    output_dir: Path = Field(Path("./cagey_output"), alias="CAGEY_OUTPUT_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


def load_settings() -> CageySettings:
    """Load settings. Separated so tests can monkeypatch easily."""
    return CageySettings()  # type: ignore[call-arg]
