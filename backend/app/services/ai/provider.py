"""AI provider abstraction.

All model calls go through `AIProvider`. Agents never import an SDK directly.
This gives one place for model configuration, failure handling, prompt
versioning and test doubles.

Phase 1 ships the interface and a Gemini provider that is configured but not yet
implemented. Phase 2 implements `GeminiProvider.generate_structured`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import ExternalServiceError, NotImplementedYetError

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class PromptSpec:
    """A versioned prompt. Templates live in app/prompts/ (Phase 2+)."""

    name: str
    version: str
    system: str
    user: str
    variables: dict[str, str] = field(default_factory=dict)


class AIProviderError(ExternalServiceError):
    code = "ai_provider_error"


class AIProvider(Protocol):
    name: str

    async def generate_structured(self, prompt: PromptSpec, schema: type[T]) -> T:
        """Return a response validated against `schema`, or raise AIProviderError."""
        ...


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self.model = model

    @property
    def configured(self) -> bool:
        return self._api_key is not None

    async def generate_structured(self, prompt: PromptSpec, schema: type[T]) -> T:
        if not self.configured:
            raise AIProviderError("GEMINI_API_KEY is not set")
        raise NotImplementedYetError("Gemini structured generation is implemented in Phase 2")


def build_ai_provider(settings: Settings) -> AIProvider:
    key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
    return GeminiProvider(api_key=key, model=settings.gemini_model)
