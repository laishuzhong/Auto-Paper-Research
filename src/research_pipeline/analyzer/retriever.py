from __future__ import annotations

import re
from collections import Counter

from ..models.schema import Chunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


class KeywordRetriever:
    def __init__(self, synonyms: list[str]) -> None:
        tokens: list[str] = []
        for synonym in synonyms:
            tokens.extend(_tokenize(synonym))
        self.synonyms = tokens

    def retrieve(self, query: str, chunks: list[Chunk], k: int) -> list[Chunk]:
        query_tokens = _tokenize(query) + self.synonyms
        query_counts = Counter(query_tokens)
        scored: list[tuple[float, Chunk]] = []
        for chunk in chunks:
            tokens = _tokenize(chunk.text)
            if not tokens:
                continue
            token_counts = Counter(tokens)
            score = 0.0
            for token, weight in query_counts.items():
                score += token_counts.get(token, 0) * weight
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]
