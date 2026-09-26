"""Local text embeddings for the civic knowledge base (Phase 3).

Default: `HashingNgramEmbedder` - a deterministic, dependency-free, multilingual
embedding built from hashed word, word-bigram and character n-gram features
(the "hashing trick"). It runs fully offline, gives the same vectors on every
machine, and works for all six scripts because it only needs characters.

Honest limits: it is LEXICAL/SUB-WORD similarity, not a neural semantic model.
Paraphrases that share no words or sub-words ("lamp is dead" vs "light not
working") are only weakly similar. That is why classification never trusts
retrieval alone: configured rules and citizen evidence must agree.

Optional: `OnnxMiniLMEmbedder` wraps ChromaDB's bundled all-MiniLM-L6-v2 ONNX
embedding (English-centric). It needs the model files, which ChromaDB downloads
on first use; it is used only when KB_EMBEDDING_PROVIDER=onnx-minilm.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from app.services.intake.offline.text import is_separator, normalise

_ENGLISH_STOPWORDS = frozenset(
    "a an the is are was were be been being am of in on at to for from by with and or not no "
    "it its this that these those there here has have had do does did my our your their his her "
    "we you they he she i me us them as so very near since about into over under than then".split()
)


class Embedder(Protocol):
    name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _tokens(text: str) -> list[str]:
    norm = normalise(text)
    tokens: list[str] = []
    current: list[str] = []
    for ch in norm:
        if is_separator(ch):
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return [t for t in tokens if t not in _ENGLISH_STOPWORDS and not re.fullmatch(r"\d+", t)]


class HashingNgramEmbedder:
    """Deterministic hashed n-gram embedding. Same input -> same vector, everywhere."""

    name = "hashing-ngram-v1"

    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    def _index(self, feature: str) -> tuple[int, float]:
        digest = int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(), "big")
        return digest % self.dimension, (1.0 if digest >> 63 == 0 else -1.0)

    def _features(self, text: str) -> dict[str, float]:
        weights: dict[str, float] = {}

        def add(feature: str, weight: float) -> None:
            weights[feature] = weights.get(feature, 0.0) + weight

        tokens = _tokens(text)
        for token in tokens:
            add(f"w:{token}", 1.0)
            padded = f"<{token}>"
            for n in (3, 4):
                for i in range(max(len(padded) - n + 1, 0)):
                    add(f"c{n}:{padded[i:i + n]}", 0.35)
        for first, second in zip(tokens, tokens[1:]):
            add(f"b:{first}_{second}", 0.8)
        return weights

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for feature, weight in self._features(text).items():
                index, sign = self._index(feature)
                vector[index] += sign * (1.0 + math.log(weight)) if weight >= 1.0 else sign * weight
            norm = math.sqrt(sum(v * v for v in vector))
            vectors.append([v / norm for v in vector] if norm > 0 else vector)
        return vectors


class OnnxMiniLMEmbedder:  # pragma: no cover - needs model files that cannot be downloaded here
    """Optional local neural embedding via ChromaDB's ONNX all-MiniLM-L6-v2 (English-centric).
    NOT TESTED in the build environment (the model download is blocked there)."""

    name = "onnx-all-minilm-l6-v2"
    dimension = 384

    def __init__(self) -> None:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        self._function = DefaultEmbeddingFunction()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._function(texts)]


def build_embedder(provider: str) -> Embedder:
    if provider == "hashing":
        return HashingNgramEmbedder()
    if provider == "onnx-minilm":
        return OnnxMiniLMEmbedder()
    raise ValueError(f"Unknown KB embedding provider {provider!r} (use 'hashing' or 'onnx-minilm')")
