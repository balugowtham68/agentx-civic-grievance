"""Speech-to-text for uploaded audio (offline first), plus audio validation.

Voice paths, in order of preference:
1. BrowserSpeechProvider - the Web Speech API in the citizen UI turns speech into
   text on the device; the text is submitted with input_channel="voice". No audio
   reaches the server. (Implemented in frontend/src/hooks/useVoiceInput.ts.)
2. LocalWhisperProvider - an on-server model (faster-whisper) loaded from
   LOCAL_STT_MODEL_PATH. Optional: used only if the package and model files are
   present; nothing is downloaded at runtime.
3. RemoteWhisperProvider (OpenAI Whisper) - OPTIONAL remote enhancement, only with
   OPENAI_API_KEY.
If none is available, POST /intake/voice answers 503 and the UI offers typing.

Audio is validated by its bytes (not the client's filename or content type),
bounded in size (and duration, for WAV), never written to disk, never stored.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import wave
from pathlib import Path

import httpx

from app.core.errors import (
    AppError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
)
from app.core.logging import get_logger
from app.services.external import Transcript

logger = get_logger(__name__)

# format -> (MIME type sent to the provider, file extension)
AUDIO_FORMATS: dict[str, tuple[str, str]] = {
    "webm": ("audio/webm", "webm"),
    "ogg": ("audio/ogg", "ogg"),
    "wav": ("audio/wav", "wav"),
    "mp3": ("audio/mpeg", "mp3"),
    "m4a": ("audio/mp4", "m4a"),
}
ACCEPTED_CONTENT_TYPES = {
    "audio/webm": "webm",
    "video/webm": "webm",  # some browsers label MediaRecorder output this way
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
}
MIN_AUDIO_BYTES = 128


class InvalidAudioError(AppError):
    status_code = 422
    code = "invalid_audio"


class SpeechToTextError(ExternalServiceError):
    code = "speech_to_text_failed"


class SpeechToTextTimeoutError(ExternalServiceTimeoutError):
    code = "speech_to_text_timeout"


class SpeechToTextUnavailableError(ServiceUnavailableError):
    code = "speech_to_text_unavailable"


def sniff_audio_format(data: bytes) -> str | None:
    """Identify the container from magic bytes."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"\x1a\x45\xdf\xa3":  # EBML (WebM/Matroska)
        return "webm"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "mp3"
    if data[4:8] == b"ftyp":
        return "m4a"
    return None


def wav_duration_seconds(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as wav:
            frames, rate = wav.getnframes(), wav.getframerate()
    except (wave.Error, EOFError) as exc:
        raise InvalidAudioError("The WAV recording is damaged or incomplete") from exc
    if rate <= 0:
        raise InvalidAudioError("The WAV recording has no sample rate")
    return frames / rate


def validate_audio(
    data: bytes, content_type: str | None, *, max_bytes: int, max_seconds: float | None = None
) -> str:
    """Return the verified audio format or raise a structured error."""
    base_type = (content_type or "").split(";")[0].strip().lower()
    if base_type not in ACCEPTED_CONTENT_TYPES:
        raise UnsupportedMediaTypeError(
            f"Unsupported audio type {base_type or 'unknown'!r}. "
            f"Accepted: {', '.join(sorted(set(ACCEPTED_CONTENT_TYPES)))}"
        )
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"Audio is larger than the {max_bytes // (1024 * 1024)} MB limit")
    if len(data) < MIN_AUDIO_BYTES:
        raise InvalidAudioError("Audio is empty or too short")
    detected = sniff_audio_format(data)
    if detected is None:
        raise InvalidAudioError("The file is not a recognised audio recording")
    # Duration can be checked without extra libraries only for WAV; other formats
    # are bounded by size (documented limitation).
    if detected == "wav" and max_seconds is not None and wav_duration_seconds(data) > max_seconds:
        raise PayloadTooLargeError(f"Recording is longer than {int(max_seconds)} seconds")
    return detected


class UnavailableTranscriptionProvider:
    """Used when no server speech-to-text is configured. Never pretends to transcribe."""

    name = "none"

    @property
    def available(self) -> bool:
        return False

    async def transcribe(self, audio: bytes, *, audio_format: str, language_hint: str | None = None) -> Transcript:
        raise SpeechToTextUnavailableError(
            "Server speech recognition is not configured. Use the microphone button in a "
            "supported browser, or type your complaint."
        )


class LocalWhisperProvider:
    """On-server speech-to-text with faster-whisper, fully offline.

    Available only when the `faster_whisper` package is installed and a model
    directory exists at LOCAL_STT_MODEL_PATH (e.g. a converted "base" model, about
    150 MB, runs on CPU). Not installed by default and not tested in this build:
    the development environment could not download model weights.
    """

    name = "local_whisper"

    def __init__(self, model_path: str | None, *, compute_type: str = "int8") -> None:
        self._path = Path(model_path) if model_path else None
        self._compute_type = compute_type
        self._model: object | None = None

    @property
    def available(self) -> bool:
        return (
            self._path is not None
            and self._path.is_dir()
            and importlib.util.find_spec("faster_whisper") is not None
        )

    def _load(self) -> object:
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            self._model = WhisperModel(str(self._path), device="cpu", compute_type=self._compute_type)
        return self._model

    async def transcribe(self, audio: bytes, *, audio_format: str, language_hint: str | None = None) -> Transcript:
        if not self.available:
            raise SpeechToTextUnavailableError("Local speech recognition model is not installed")

        def run() -> str:
            model = self._load()
            segments, _info = model.transcribe(  # type: ignore[attr-defined]
                io.BytesIO(audio), language=language_hint.split("-")[0] if language_hint else None
            )
            return " ".join(segment.text.strip() for segment in segments).strip()

        try:
            text = await asyncio.to_thread(run)
        except SpeechToTextUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 - model/codec errors become a safe error
            raise SpeechToTextError("Local speech recognition failed on this recording") from exc
        if not text:
            raise InvalidAudioError("No speech was recognised in the recording. Please try again or type")
        return Transcript(text=text, language=language_hint, provider=self.name)


class ChainTranscriptionProvider:
    """Tries each available provider in order (local first). A provider that is not
    available is skipped; a real failure is reported, not silently retried remotely."""

    def __init__(self, providers: list[object]) -> None:
        self._providers = providers
        self.name = "+".join(getattr(p, "name", "?") for p in providers) or "none"

    @property
    def available(self) -> bool:
        return any(getattr(p, "available", False) for p in self._providers)

    @property
    def available_names(self) -> list[str]:
        return [p.name for p in self._providers if getattr(p, "available", False)]  # type: ignore[attr-defined]

    async def transcribe(self, audio: bytes, *, audio_format: str, language_hint: str | None = None) -> Transcript:
        for provider in self._providers:
            if getattr(provider, "available", False):
                return await provider.transcribe(audio, audio_format=audio_format, language_hint=language_hint)  # type: ignore[attr-defined]
        return await UnavailableTranscriptionProvider().transcribe(audio, audio_format=audio_format)


class WhisperTranscriptionProvider:
    """OPTIONAL remote OpenAI Whisper over HTTP (httpx). Credentials only from the environment."""

    name = "remote_whisper"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "whisper-1",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._url = f"{base_url.rstrip('/')}/audio/transcriptions"
        self._timeout = timeout_seconds
        self._transport = transport

    @property
    def available(self) -> bool:
        return True

    async def transcribe(self, audio: bytes, *, audio_format: str, language_hint: str | None = None) -> Transcript:
        mime, extension = AUDIO_FORMATS[audio_format]
        data = {"model": self._model, "response_format": "json"}
        if language_hint:
            data["language"] = language_hint.split("-")[0]
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    data=data,
                    # A fixed server-side filename: the client's filename is never used.
                    files={"file": (f"recording.{extension}", audio, mime)},
                )
        except httpx.TimeoutException as exc:
            raise SpeechToTextTimeoutError("Speech recognition took too long. Please try again or type your complaint") from exc
        except httpx.HTTPError as exc:
            raise SpeechToTextError("Speech recognition service could not be reached") from exc

        if response.status_code >= 400:
            logger.warning("speech-to-text http error", extra={"status": response.status_code})
            raise SpeechToTextError(f"Speech recognition failed (HTTP {response.status_code})")
        try:
            text = str(response.json().get("text", "")).strip()
        except ValueError as exc:
            raise SpeechToTextError("Speech recognition returned an unexpected response") from exc
        if not text:
            raise InvalidAudioError("No speech was recognised in the recording. Please try again or type")
        # Whisper's json response has no confidence score; none is invented.
        return Transcript(text=text, language=language_hint, provider=f"remote_whisper:{self._model}")
