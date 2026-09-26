"""Translation for downstream processing.

The citizen's original text is always kept. Translation output is used only as
a convenience for later phases (e.g. RAG in English); it is never a source of
facts - facts are extracted and verified against the citizen's own words.
"""

from __future__ import annotations

from app.prompts.intake import AITranslationOutput, translation_prompt
from app.services.ai import AIProvider, AIProviderError
from app.services.external import Translation


class AITranslationProvider:
    name = "ai_translation"

    def __init__(self, ai: AIProvider) -> None:
        self._ai = ai
        self.name = f"{ai.name}:{ai.model}"

    @property
    def available(self) -> bool:
        return self._ai.available

    async def translate(self, text: str, *, source_language: str, target_language: str) -> Translation:
        output = await self._ai.generate_structured(
            translation_prompt(text, source_language, target_language), AITranslationOutput
        )
        translated = output.translated_text.strip()
        if not translated:
            raise AIProviderError("The AI service returned an empty translation")
        return Translation(
            text=translated,
            source_language=source_language,
            target_language=target_language,
            provider=self.name,
        )
