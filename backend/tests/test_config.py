"""Configuration loading and fail-fast rules."""

import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings


def test_development_starts_without_secrets() -> None:
    settings = Settings(_env_file=None, app_env=AppEnvironment.DEVELOPMENT)

    assert settings.gemini_api_key is None
    assert settings.is_sqlite


def test_values_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173, http://127.0.0.1:5173")
    monkeypatch.setenv("GEMINI_API_KEY", "abc")

    settings = Settings(_env_file=None)

    assert settings.app_env is AppEnvironment.TEST
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "abc"


def test_blank_secret_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "   ")

    assert Settings(_env_file=None).gemini_api_key is None


def test_production_fails_clearly_when_secrets_missing() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        Settings(_env_file=None, app_env=AppEnvironment.PRODUCTION)


def test_production_accepts_complete_secrets() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.PRODUCTION,
        gemini_api_key="k1",
        mock_gov_api_key="k2",
    )
    assert settings.app_env is AppEnvironment.PRODUCTION


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(_env_file=None, log_level="LOUD")


def test_secrets_hidden_in_repr_and_summary() -> None:
    settings = Settings(_env_file=None, gemini_api_key="very-secret")

    assert "very-secret" not in repr(settings)
    assert "very-secret" not in str(settings.summary())
