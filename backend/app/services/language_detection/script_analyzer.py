"""Unicode and script-level language analyzer."""

from __future__ import annotations

import unicodedata
from app.services.language_detection.schemas import ScriptSignal

SCRIPT_RANGES: dict[str, tuple[int, int, str]] = {
    "Telugu": (0x0C00, 0x0C7F, "te"),
    "Tamil": (0x0B80, 0x0BFF, "ta"),
    "Kannada": (0x0C80, 0x0CFF, "kn"),
    "Malayalam": (0x0D00, 0x0D7F, "ml"),
    "Devanagari": (0x0900, 0x097F, "hi"),
    "Bengali": (0x0980, 0x09FF, "bn"),
    "Gujarati": (0x0A80, 0x0AFF, "gu"),
    "Gurmukhi": (0x0A00, 0x0A7F, "pa"),
    "Oriya": (0x0B00, 0x0B7F, "or"),
}


class ScriptAnalyzer:
    """Analyzes character scripts and code-mixing in text."""

    def analyze(self, text: str) -> ScriptSignal:
        if not text:
            return ScriptSignal()

        counts: dict[str, int] = {}
        total_letters = 0
        latin_count = 0
        native_count = 0

        for ch in text:
            if not unicodedata.category(ch).startswith(("L", "M")):
                continue
            total_letters += 1
            code = ord(ch)

            if code < 0x0250:
                latin_count += 1
                counts["Latin"] = counts.get("Latin", 0) + 1
                continue

            matched = False
            for script_name, (lo, hi, _) in SCRIPT_RANGES.items():
                if lo <= code <= hi:
                    counts[script_name] = counts.get(script_name, 0) + 1
                    native_count += 1
                    matched = True
                    break

            if not matched:
                counts["Other"] = counts.get("Other", 0) + 1

        if total_letters == 0:
            return ScriptSignal()

        # Find Indic scripts present
        indic_scripts = {s: c for s, c in counts.items() if s not in ("Latin", "Other")}
        top_indic_script = max(indic_scripts, key=lambda s: indic_scripts[s]) if indic_scripts else None
        top_indic_count = indic_scripts[top_indic_script] if top_indic_script else 0

        # If any Indic script has meaningful presence (>= 3 chars or >= 15% of text),
        # it is the true base language of a code-mixed Indian grievance
        if top_indic_script and (top_indic_count >= 3 or (top_indic_count / total_letters) >= 0.15):
            dominant = top_indic_script
            script_lang = SCRIPT_RANGES[dominant][2]
        else:
            dominant = max(counts, key=lambda s: counts[s])
            script_lang = "en" if dominant == "Latin" else (SCRIPT_RANGES[dominant][2] if dominant in SCRIPT_RANGES else None)

        native_ratio = round(native_count / total_letters, 3)
        latin_ratio = round(latin_count / total_letters, 3)
        is_code_mixed = native_count > 0 and latin_count > 0

        return ScriptSignal(
            dominant_script=dominant,
            script_language=script_lang,
            native_char_ratio=native_ratio,
            latin_char_ratio=latin_ratio,
            is_code_mixed=is_code_mixed,
        )
