"""Text utilities for the offline intake engine.

- `normalise_with_map` lower-cases and cleans text (zero-width joiners, Malayalam
  chillu sequences, curly quotes) while remembering where each character came from,
  so every match can be reported as an exact slice of the citizen's original words.
- `PhraseMatcher` finds configured phrases with script-aware boundaries:
  Indic scripts attach suffixes to words, so "prefix" patterns may be followed by
  more letters ("தெரு" matches "தெருவுல"); "word" patterns must stand alone.
  Short Latin patterns always need a word boundary so "en" never matches "open".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

_ZERO_WIDTH = {"‌", "‍", "﻿"}
_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', " ": " "}
# Malayalam chillu written as consonant + virama + ZWJ -> atomic chillu letter.
_CHILLU = {"ണ": "ൺ", "ന": "ൻ", "ര": "ർ", "ല": "ൽ", "ള": "ൾ"}
_TOKEN_RE = re.compile(r"[^\s,.;:!?()\[\]\"'।॥]+")


def _normalise_with_spans(text: str) -> tuple[str, list[int], list[int]]:
    """Normalised text plus, for each normalised character, the start and end (exclusive)
    of the original characters it came from (a Malayalam chillu comes from 3 characters)."""
    text = unicodedata.normalize("NFC", text)
    out: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _CHILLU and text[i + 1 : i + 3] == "്‍":
            out.append(_CHILLU[ch])
            starts.append(i)
            ends.append(i + 3)
            i += 3
            continue
        if ch in _ZERO_WIDTH:
            i += 1
            continue
        ch = _QUOTES.get(ch, ch)
        if ch.isspace():
            if out and out[-1] == " ":
                i += 1
                continue
            ch = " "
        for lowered in ch.lower():
            out.append(lowered)
            starts.append(i)
            ends.append(i + 1)
        i += 1
    return "".join(out), starts, ends


def normalise_with_map(text: str) -> tuple[str, list[int]]:
    norm, starts, _ = _normalise_with_spans(text)
    return norm, starts


def normalise(text: str) -> str:
    return normalise_with_map(text)[0].strip()


def is_separator(ch: str) -> bool:
    return ch.isspace() or unicodedata.category(ch)[0] in {"P", "S", "Z"}


def is_latin(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(ord(c) < 0x0250 for c in letters)


@dataclass(frozen=True)
class Span:
    start: int  # indices into the normalised text
    end: int
    value: str  # configured English gloss / id
    kind: str  # which resource list matched


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str


class NormalisedText:
    """A citizen statement with its normalised form and token positions."""

    def __init__(self, original: str) -> None:
        # NFC first so slices come from the same text the offsets refer to.
        self.original = unicodedata.normalize("NFC", original)
        self.norm, self._origin, self._origin_end = _normalise_with_spans(self.original)
        self.tokens = [Token(m.start(), m.end(), m.group(0)) for m in _TOKEN_RE.finditer(self.norm)]

    def original_slice(self, start: int, end: int) -> str:
        """Exact citizen words for a span of the normalised text."""
        if start >= end:
            return ""
        return self.original[self._origin[start] : self._origin_end[end - 1]].strip()

    def token_index_at(self, position: int) -> int | None:
        for index, token in enumerate(self.tokens):
            if token.start <= position < token.end:
                return index
        return None


Mode = Literal["prefix", "word"]


class PhraseMatcher:
    """Matches a list of (pattern, value) pairs; longest match wins on overlap."""

    def __init__(self, entries: list[tuple[str, str]], kind: str, mode: Mode) -> None:
        normalised = [(normalise(p), v) for p, v in entries if normalise(p)]
        self._entries = sorted(normalised, key=lambda e: len(e[0]), reverse=True)
        self.kind = kind
        self.mode = mode

    def _right_ok(self, text: str, end: int, pattern: str) -> bool:
        if end >= len(text) or is_separator(text[end]):
            return True
        if self.mode == "word":
            return False
        # Short Latin patterns ("en", "lo", "maa") must be whole words.
        return not (is_latin(pattern) and len(pattern) <= 3)

    def find(self, text: NormalisedText) -> list[Span]:
        spans: list[Span] = []
        taken: list[tuple[int, int]] = []
        norm = text.norm
        for pattern, value in self._entries:
            start = norm.find(pattern)
            while start != -1:
                end = start + len(pattern)
                left_ok = start == 0 or is_separator(norm[start - 1])
                if left_ok and self._right_ok(norm, end, pattern) and not any(
                    s < end and start < e for s, e in taken
                ):
                    spans.append(Span(start, end, value, self.kind))
                    taken.append((start, end))
                start = norm.find(pattern, start + 1)
        return sorted(spans, key=lambda s: s.start)
