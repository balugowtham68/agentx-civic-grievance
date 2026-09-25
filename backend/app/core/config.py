"""Centralised application configuration.

All settings come from environment variables (optionally via a `.env` file in the
repository root or in `backend/`). Secrets are held as `SecretStr` so they are never
printed in logs or reprs.

Rules:
- development / test: secrets are optional so the app starts without keys.
- production: missing required secrets fail fast at startup with a clear message.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AGENT X"
    app_version: str = "0.1.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    log_level: str = "INFO"

    # Persistence
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'agentx.db').as_posix()}"

    # HTTP
    frontend_origin: str = "http://localhost:5173"

    # AI provider (Phase 2+). Never exposed to the frontend.
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"

    # Mock Government Grievance API (Phase 5). Hackathon mock only.
    mock_gov_api_base_url: str = "http://localhost:8001/mock-gov/v1"
    mock_gov_api_key: SecretStr | None = None

    # Knowledge base (Phase 3 indexes it into ChromaDB).
    knowledge_base_dir: Path = Field(default=REPO_ROOT / "knowledge_base")

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"LOG_LEVEL must be a standard logging level, got {value!r}")
        return level

    @field_validator("gemini_api_key", "mock_gov_api_key", mode="before")
    @classmethod
    def _blank_secret_is_none(cls, value: object) -> object:
        # An empty `GEMINI_API_KEY=` line in .env means "not set".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _require_production_secrets(self) -> "Settings":
        if self.app_env is AppEnvironment.PRODUCTION:
            missing = [
                name.upper()
                for name in ("gemini_api_key", "mock_gov_api_key")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    "Missing required secrets for APP_ENV=production: " + ", ".join(missing)
                )
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    def summary(self) -> dict[str, object]:
        """Non-secret view of configuration, safe to log or return from /health."""
        return {
            "app_env": self.app_env.value,
            "log_level": self.log_level,
            "database": "sqlite" if self.is_sqlite else "other",
            "gemini_configured": self.gemini_api_key is not None,
            "mock_gov_configured": self.mock_gov_api_key is not None,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
