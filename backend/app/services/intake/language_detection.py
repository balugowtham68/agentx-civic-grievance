"""Language detection for citizen intake (offline first).

Order (the citizen's own choice is handled before this, by the agent):
    1. ScriptLanguageDetector - Unicode block of Indian scripts. Deterministic.
    2. LatinHeuristicDetector - Latin-script text: counts configured marker words
       per language (English function words; romanised Tamil/Telugu/Hindi/...
       words from backend/resources/intake/<lang>.json). Deterministic.
    3. AILanguageDetector - OPTIONAL, only if the heuristics are inconclusive.
    4. English only when English marker words justify it (method="default");
       otherwise "und" and the citizen is asked to choose.

No detector invents a confidence value (`confidence` is None).
Limitation: Devanagari maps to Hindi; Marathi/Nepali need explicit selection.
"""

from __future__ import annotations

import re
import unicodedata

from app.core.languages import LanguageRegistry
from app.core.logging import get_logger
from app.prompts.intake import AILanguageOutput, language_prompt
from app.services.ai import AIProvider, AIProviderError
from app.services.external import DetectedLanguage
from app.services.intake.offline.text import normalise

logger = get_logger(__name__)

UNDETERMINED = "und"

# Unicode blocks (a fact about scripts, not language configuration).
SCRIPT_BLOCKS: dict[str, tuple[int, int]] = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Gujarati": (0x0A80, 0x0AFF),
    "Oriya": (0x0B00, 0x0B7F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Kannada": (0x0C80, 0x0CFF),
    "Malayalam": (0x0D00, 0x0D7F),
}


def dominant_script(text: str) -> str | None:
    counts: dict[str, int] = {}
    for ch in text:
        if not unicodedata.category(ch).startswith(("L", "M")):
            continue
        point = ord(ch)
        script = "Latin" if point < 0x0250 else next(
            (name for name, (lo, hi) in SCRIPT_BLOCKS.items() if lo <= point <= hi), "Other"
        )
        counts[script] = counts.get(script, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda name: counts[name])


class ScriptLanguageDetector:
    def __init__(self, registry: LanguageRegistry) -> None:
        self._by_script = {}
        for language in registry.enabled():
            self._by_script.setdefault(language.script, language.code)

    def detect_sync(self, text: str) -> DetectedLanguage:
        script = dominant_script(text)
        if script is None:
            return DetectedLanguage(language=UNDETERMINED, method="script", script=None)
        if script == "Latin":
            # Could be English or a romanised Indian language: ambiguous.
            return DetectedLanguage(language="en", method="default", script="Latin")
        code = self._by_script.get(script, UNDETERMINED)
        return DetectedLanguage(language=code, method="script", script=script)

    async def detect(self, text: str) -> DetectedLanguage:
        return self.detect_sync(text)


class LatinHeuristicDetector:
    """Marker-word vote for Latin-script text. Needs >= 2 markers and a clear lead,
    except English, which may win on 1 marker when no other language scores."""

    def __init__(self, markers: dict[str, set[str]]) -> None:
        self._markers = markers

    def scores(self, text: str) -> dict[str, int]:
        tokens = set(re.findall(r"[a-z]+", normalise(text)))
        return {code: len(tokens & words) for code, words in self._markers.items()}

    def detect_sync(self, text: str) -> DetectedLanguage | None:
        scores = sorted(self.scores(text).items(), key=lambda item: item[1], reverse=True)
        if not scores or scores[0][1] == 0:
            return None
        (best, top), second = scores[0], (scores[1][1] if len(scores) > 1 else 0)
        if top > second and (top >= 2 or (best == "en" and second == 0)):
            return DetectedLanguage(
                language=best, method="heuristic", transliterated=best != "en", script="Latin"
            )
        return None


class AILanguageDetector:
    def __init__(self, ai: AIProvider, registry: LanguageRegistry) -> None:
        self._ai = ai
        self._codes = [language.code for language in registry.enabled()]

    @property
    def available(self) -> bool:
        return self._ai.available

    async def detect(self, text: str) -> DetectedLanguage:
        output = await self._ai.generate_structured(language_prompt(text, self._codes), AILanguageOutput)
        code = output.language.strip().lower()
        if not (2 <= len(code) <= 3 and code.isalpha()):
            code = UNDETERMINED
        return DetectedLanguage(
            language=code, method="provider", transliterated=output.transliterated, script="Latin"
        )


class CompositeLanguageDetector:
    def __init__(
        self,
        script: ScriptLanguageDetector,
        ai: AILanguageDetector | None = None,
        latin: LatinHeuristicDetector | None = None,
    ) -> None:
        self._script = script
        self._ai = ai
        self._latin = latin

    async def detect(self, text: str) -> DetectedLanguage:
        result = self._script.detect_sync(text)
        if result.method != "default":
            return result  # non-Latin script: deterministic answer
        if self._latin is not None:
            heuristic = self._latin.detect_sync(text)
            if heuristic is not None:
                return heuristic
        if self._ai is not None and self._ai.available:
            try:
                return await self._ai.detect(text)
            except AIProviderError as exc:
                logger.warning("ai language detection failed", extra={"error_code": exc.code})
        if self._latin is not None and self._latin.scores(text).get("en", 0) == 0:
            # Nothing supports English: do not pretend. The citizen is asked to choose.
            return DetectedLanguage(language=UNDETERMINED, method="default", script="Latin")
        return result
