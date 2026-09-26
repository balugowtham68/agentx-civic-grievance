"""AI provider abstraction and the Gemini implementation.

All model calls go through `AIProvider`. Agents never import an SDK or call a
model API directly. This gives one place for model configuration, timeouts,
failure handling, prompt versioning and test doubles.

GeminiProvider talks to the Gemini REST API with httpx (already a dependency),
so no vendor SDK is needed. The API key is sent in a header - never in the URL -
and never appears in errors or logs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger

T = TypeVar("T", bound=BaseModel)
logger = get_logger(__name__)


@dataclass(frozen=True)
class PromptSpec:
    """A versioned prompt. Builders live in app/prompts/."""

    name: str
    version: str
    system: str
    user: str
    variables: dict[str, str] = field(default_factory=dict)


class AIProviderError(ExternalServiceError):
    code = "ai_provider_error"


class AIProviderTimeoutError(AIProviderError):
    status_code = 504
    code = "ai_provider_timeout"


class AIProviderUnavailableError(AIProviderError):
    status_code = 503
    code = "ai_provider_unavailable"


class AIProvider(Protocol):
    name: str
    model: str

    @property
    def available(self) -> bool: ...

    async def generate_structured(self, prompt: PromptSpec, schema: type[T]) -> T:
        """Return a response validated against `schema`, or raise AIProviderError."""
        ...


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    return _FENCE_RE.sub("", text.strip())


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        *,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 20.0,
        max_output_tokens: int = 1024,
        max_attempts: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._max_attempts = max(1, max_attempts)
        self._transport = transport

    @property
    def configured(self) -> bool:
        return self._api_key is not None

    @property
    def available(self) -> bool:
        return self.configured

    def _request_body(self, prompt: PromptSpec, schema: type[BaseModel]) -> dict[str, object]:
        schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"))
        system = (
            f"{prompt.system}\n\nRespond with a single JSON object only, no prose, that "
            f"validates against this JSON Schema:\n{schema_json}"
        )
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "maxOutputTokens": self._max_output_tokens,
            },
        }

    async def _call(self, body: dict[str, object], prompt: PromptSpec) -> str:
        url = f"{self._base_url}/models/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(
                    url, json=body, headers={"x-goog-api-key": self._api_key or ""}
                )
        except httpx.TimeoutException as exc:
            logger.warning("ai provider timeout", extra={"prompt": prompt.name})
            raise AIProviderTimeoutError("The AI service took too long to respond") from exc
        except httpx.HTTPError as exc:
            logger.warning("ai provider transport error", extra={"prompt": prompt.name, "error_type": type(exc).__name__})
            raise AIProviderError("The AI service could not be reached") from exc

        if response.status_code == 429:
            raise AIProviderError("The AI service is busy (rate limited). Please try again shortly")
        if response.status_code >= 400:
            # The body is not echoed: it may contain request details.
            logger.warning("ai provider http error", extra={"prompt": prompt.name, "status": response.status_code})
            raise AIProviderError(f"The AI service returned an error (HTTP {response.status_code})")

        try:
            data = response.json()
            candidate = data["candidates"][0]
            if candidate.get("finishReason") not in (None, "STOP", "MAX_TOKENS"):
                raise AIProviderError(f"The AI service declined to answer ({candidate.get('finishReason')})")
            return "".join(part.get("text", "") for part in candidate["content"]["parts"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError("The AI service returned an unexpected response") from exc

    async def generate_structured(self, prompt: PromptSpec, schema: type[T]) -> T:
        if not self.configured:
            raise AIProviderUnavailableError("GEMINI_API_KEY is not set")
        body = self._request_body(prompt, schema)
        for attempt in range(1, self._max_attempts + 1):
            text = await self._call(body, prompt)
            try:
                return schema.model_validate_json(_strip_code_fences(text))
            except ValidationError:
                logger.warning(
                    "ai provider output failed validation",
                    extra={"prompt": prompt.name, "version": prompt.version, "attempt": attempt},
                )
        raise AIProviderError("The AI service returned output in an unexpected format")


def build_ai_provider(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> AIProvider:
    return GeminiProvider(
        api_key=settings.secret("gemini_api_key"),
        model=settings.gemini_model,
        base_url=settings.gemini_base_url,
        timeout_seconds=settings.ai_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
        transport=transport,
    )
