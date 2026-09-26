"""Basic input sanitisation for citizen free text.

This is hygiene, not a full security layer: it removes markup and control
characters and normalises whitespace so stored text is safe to render and to
send to the AI provider. Pydantic schemas enforce length limits.
"""

from __future__ import annotations

import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]*>")
_SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
# Zero-width non-joiner / joiner are part of correct spelling in Indic scripts (Malayalam chillu,
# Hindi/Kannada half forms), so they are kept. Other format characters (e.g. bidi overrides) are dropped.
_KEEP_FORMAT_CHARS = {"\u200c", "\u200d"}


def sanitize_text(value: str) -> str:
    """Return citizen text with markup and control characters removed.

    Keeps all scripts/languages (Telugu, Hindi, etc.) intact.
    """
    text = unicodedata.normalize("NFC", value)
    text = _SCRIPT_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    # Drop control/format characters except newline, tab and the Indic joiners.
    text = "".join(
        ch for ch in text if ch in "\n\t" or ch in _KEEP_FORMAT_CHARS or unicodedata.category(ch)[0] != "C"
    )
    text = text.replace("\r", "")
    text = _WS_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()
