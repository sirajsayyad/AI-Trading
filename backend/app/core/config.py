"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Application ─────────────────────────────────────
    app_name: str = "AI Trading Platform"
    app_version: str = "0.1.0"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() == "release":
            return False
        return value

    # ─── Database ────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://ai_trading:changeme_in_production@localhost:5432/ai_trading"

    # ─── Redis ───────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Security ────────────────────────────────────────
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ─── CORS ────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ─── AI / LLM ───────────────────────────────────────
    anthropic_api_key: str = ""
    market_data_provider: str = "twelve_data"
    twelve_data_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_data_feed: str = "iex"
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"
    alpha_vantage_api_key: str = ""
    enable_live_trading: bool = False

    # ─── Server ──────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
