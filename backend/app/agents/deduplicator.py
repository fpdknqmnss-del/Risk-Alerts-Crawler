from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from app.sources.base import NormalizedNewsItem

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
_STOP_WORDS = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "were",
    "will",
    "would",
    "into",
    "about",
    "after",
    "before",
    "under",
    "over",
    "their",
    "there",
    "where",
    "report",
    "reports",
    "said",
}


@dataclass(slots=True)
class SimilarityResult:
    is_duplicate: bool
    score: float


class DeduplicationService:
    """Text-embedding style deduplication using hashed token vectors."""

    def __init__(
        self,
        similarity_threshold: float = 0.90,
        embedding_dimensions: int = 256,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.embedding_dimensions = max(64, embedding_dimensions)
        self._indexed_vectors: list[list[float]] = []

    def index_existing_alert_texts(self, texts: list[str]) -> None:
        for text in texts:
            vector = self._vectorize(text)
            if vector is not None:
                self._indexed_vectors.append(vector)

    def is_duplicate_news_item(self, item: NormalizedNewsItem) -> SimilarityResult:
        text = self._news_item_text(item)
        return self.is_duplicate_text(text)

    def is_duplicate_text(self, text: str) -> SimilarityResult:
        query_vector = self._vectorize(text)
        if query_vector is None or not self._indexed_vectors:
            return SimilarityResult(is_duplicate=False, score=0.0)

        top_score = max(self._cosine_similarity(query_vector, existing) for existing in self._indexed_vectors)
        return SimilarityResult(
            is_duplicate=top_score >= self.similarity_threshold,
            score=top_score,
        )

    def register_news_item(self, item: NormalizedNewsItem, summary: str | None = None) -> None:
        text = self._news_item_text(item)
        if summary:
            text = f"{text}\n{summary}"
        vector = self._vectorize(text)
        if vector is not None:
            self._indexed_vectors.append(vector)

    def _news_item_text(self, item: NormalizedNewsItem) -> str:
        return " ".join(
            part
            for part in [
                item.title,
                item.description,
                item.content,
                item.country,
                item.region,
                item.source,
            ]
            if part
        )

    def _vectorize(self, text: str) -> list[float] | None:
        tokens = [
            token
            for token in _TOKEN_PATTERN.findall(text.lower())
            if token not in _STOP_WORDS
        ]
        if not tokens:
            return None

        vector = [0.0] * self.embedding_dimensions
        for token in tokens:
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.embedding_dimensions
            vector[index] += 1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return None

        return [value / magnitude for value in vector]

    def _cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float:
        return sum(value_a * value_b for value_a, value_b in zip(vector_a, vector_b))
