"""Centralised application configuration.

All settings come from environment variables (optionally via a `.env` file in the
repository root or in `backend/`). Secrets are held as `SecretStr` so they are never
printed in logs or reprs.

Rules:
- The system is offline-first: no secret is required in any environment. GEMINI_API_KEY
  and OPENAI_API_KEY only enable optional AI wording / remote speech-to-text, and
  MOCK_GOV_API_KEY belongs to Phase 5 (filing), which is not implemented.
- A secret is required only by the feature that uses it (e.g. SPEECH_TO_TEXT_PROVIDER=whisper
  requires OPENAI_API_KEY) and fails fast at startup with a clear message.
- production: unsafe settings (wildcard CORS, DEBUG logging) fail fast at startup.
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

    app_name: str = "SPANDAN AI"
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
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ai_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    ai_max_output_tokens: int = Field(default=1024, ge=64, le=8192)

    # Citizen intake (Phase 2)
    # Server speech-to-text for uploaded audio: "auto" (local model if installed,
    # then remote Whisper if a key is set), "local", "whisper" or "none".
    # Browser speech recognition (Web Speech API) works without any of this.
    speech_to_text_provider: str = "auto"
    local_stt_model_path: str | None = None
    max_audio_seconds: float = Field(default=120.0, gt=0, le=600)
    openai_api_key: SecretStr | None = None
    whisper_model: str = "whisper-1"
    whisper_base_url: str = "https://api.openai.com/v1"
    stt_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    max_audio_bytes: int = Field(default=10 * 1024 * 1024, gt=0, le=25 * 1024 * 1024)

    # Mock Government Grievance API (Phase 5). Hackathon mock only.
    mock_gov_api_base_url: str = "http://localhost:8001/mock-gov/v1"
    mock_gov_api_key: SecretStr | None = None

    # Civic knowledge base (Phase 3): configuration in knowledge_base/, indexed into a
    # local ChromaDB collection. No external vector database or embedding API.
    knowledge_base_dir: Path = Field(default=REPO_ROOT / "knowledge_base")
    kb_vector_dir: Path = Field(default=BACKEND_DIR / "data" / "chroma")
    # "hashing" (default, offline, deterministic) or "onnx-minilm" (optional local model).
    kb_embedding_provider: str = "hashing"
    # Re-ingest automatically at start-up when the collection is missing or stale.
    # With false, a stale/missing KB makes classification return 503 until
    # `python scripts/ingest_civic_kb.py` is run.
    kb_auto_ingest: bool = True

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"LOG_LEVEL must be a standard logging level, got {value!r}")
        return level

    @field_validator("gemini_api_key", "mock_gov_api_key", "openai_api_key", mode="before")
    @classmethod
    def _blank_secret_is_none(cls, value: object) -> object:
        # An empty `GEMINI_API_KEY=` line in .env means "not set".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("speech_to_text_provider")
    @classmethod
    def _known_stt_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"auto", "local", "none", "whisper"}:
            raise ValueError("SPEECH_TO_TEXT_PROVIDER must be 'auto', 'local', 'whisper' or 'none'")
        return value

    @field_validator("kb_embedding_provider")
    @classmethod
    def _known_embedder(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"hashing", "onnx-minilm"}:
            raise ValueError("KB_EMBEDDING_PROVIDER must be 'hashing' or 'onnx-minilm'")
        return value

    @model_validator(mode="after")
    def _check_required_settings(self) -> "Settings":
        if self.speech_to_text_provider == "whisper" and self.openai_api_key is None:
            raise ValueError("SPEECH_TO_TEXT_PROVIDER=whisper requires OPENAI_API_KEY")
        if self.app_env is AppEnvironment.PRODUCTION:
            problems = []
            if "*" in self.cors_origins:
                problems.append("FRONTEND_ORIGIN must list explicit origins, not '*'")
            if self.log_level == "DEBUG":
                problems.append("LOG_LEVEL=DEBUG is not allowed (debug logs may contain citizen text)")
            if problems:
                raise ValueError("Unsafe settings for APP_ENV=production: " + "; ".join(problems))
        return self

    def secret(self, name: str) -> str | None:
        """Plain value of a secret setting, for passing to a provider client only."""
        value = getattr(self, name)
        if value is None:
            return None
        return value.get_secret_value() if isinstance(value, SecretStr) else str(value)

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
            "speech_to_text_provider": self.speech_to_text_provider,
            "kb_embedding_provider": self.kb_embedding_provider,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
