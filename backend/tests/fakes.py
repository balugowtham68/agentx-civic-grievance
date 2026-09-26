"""Test doubles for intake providers. Deterministic, offline, clearly fake."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel

from app.services.ai import AIProviderError, PromptSpec

Response = dict[str, Any] | Exception | Callable[[PromptSpec], dict[str, Any]]


class FakeAIProvider:
    """Returns canned JSON per prompt name ("intake.extract", "intake.translate",
    "intake.detect_language"). Records every prompt it receives."""

    name = "fake-ai"
    model = "fake-model"

    def __init__(self, responses: dict[str, Response] | None = None, *, available: bool = True) -> None:
        self.responses = responses or {}
        self._available = available
        self.calls: list[PromptSpec] = []

    @property
    def available(self) -> bool:
        return self._available

    async def generate_structured(self, prompt: PromptSpec, schema: type[BaseModel]) -> Any:
        self.calls.append(prompt)
        response = self.responses.get(prompt.name)
        if response is None:
            raise AIProviderError(f"fake provider has no response for {prompt.name}")
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(prompt)
        return schema.model_validate(response)

    def calls_named(self, name: str) -> list[PromptSpec]:
        return [c for c in self.calls if c.name == name]


def fact(value: str, evidence: str, index: int = 0) -> dict[str, Any]:
    return {"value": value, "evidence": evidence, "statement_index": index}


def gemini_reply(payload: dict[str, Any] | str, status: int = 200) -> httpx.Response:
    import json

    text = payload if isinstance(payload, str) else json.dumps(payload)
    return httpx.Response(
        status, json={"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}
    )


# Minimal valid-looking audio containers (magic bytes + padding).
WAV_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEfmt " + b"\x00" * 400
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"\x00" * 400


def wav_bytes(seconds: float, rate: int = 8000) -> bytes:
    """A real, silent, mono 16-bit WAV of the given length (for duration checks)."""
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x00" * int(seconds * rate))
    return buffer.getvalue()
