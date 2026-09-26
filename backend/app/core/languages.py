"""Configurable language registry (backend/config/languages.json).

All language knowledge (codes, names, speech locales, honest support levels)
lives in that file. Code asks the registry; nothing else hard-codes languages.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.core.errors import AppError, ErrorDetail


class SupportLevel(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    FALLBACK = "FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"


class LanguageSupport(BaseModel):
    text_intake: SupportLevel
    speech_to_text: SupportLevel
    translation: SupportLevel
    ui: SupportLevel


class LanguageConfig(BaseModel):
    code: str = Field(pattern=r"^[a-z]{2,3}$")
    display_name: str
    native_name: str
    script: str
    speech_locale: str
    enabled: bool = True
    support: LanguageSupport
    notes: str = ""


class LanguageRegistryFile(BaseModel):
    processing_language: str
    items: list[LanguageConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "LanguageRegistryFile":
        codes = [item.code for item in self.items]
        if len(codes) != len(set(codes)):
            raise ValueError("duplicate language codes in languages.json")
        if self.processing_language not in codes:
            raise ValueError("processing_language must be a configured language")
        return self


class UnsupportedLanguageError(AppError):
    status_code = 422
    code = "unsupported_language"


DEFAULT_LANGUAGES_FILE = Path(__file__).resolve().parents[2] / "config" / "languages.json"


class LanguageRegistry:
    def __init__(self, data: LanguageRegistryFile) -> None:
        self._data = data
        self._by_code = {item.code: item for item in data.items}

    @classmethod
    def load(cls, path: Path = DEFAULT_LANGUAGES_FILE) -> "LanguageRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(LanguageRegistryFile(**raw))

    @property
    def processing_language(self) -> str:
        return self._data.processing_language

    def all(self) -> list[LanguageConfig]:
        return list(self._data.items)

    def enabled(self) -> list[LanguageConfig]:
        return [item for item in self._data.items if item.enabled]

    def get(self, code: str | None) -> LanguageConfig | None:
        if code is None:
            return None
        return self._by_code.get(code.split("-")[0].lower())

    def is_enabled(self, code: str | None) -> bool:
        language = self.get(code)
        return language is not None and language.enabled

    def require_enabled(self, code: str) -> LanguageConfig:
        language = self.get(code)
        if language is None or not language.enabled:
            supported = ", ".join(item.code for item in self.enabled())
            raise UnsupportedLanguageError(
                f"Language {code!r} is not supported. Choose one of: {supported}",
                details=[ErrorDetail(field="language", message=f"Supported: {supported}")],
            )
        return language
