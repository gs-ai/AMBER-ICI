"""Deterministic case-bounded chunking and sparse retrieval."""

from __future__ import annotations

import hashlib
import heapq
import math
import re
from collections import Counter
from typing import Iterable


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or ""))]


def chunk_text(text: str, size: int = 1600, overlap: int = 200) -> list[str]:
    """Split on word boundaries with bounded character overlap."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []
    size = max(400, min(int(size), 8_000))
    overlap = max(0, min(int(overlap), size // 2))
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


def build_chunks(artifact_id: str, text: str) -> list[dict]:
    chunks = []
    for ordinal, body in enumerate(chunk_text(text)):
        digest = hashlib.sha256(f"{artifact_id}:{ordinal}:{body}".encode("utf-8")).hexdigest()
        chunks.append(
            {
                "id": f"chunk_{digest[:24]}",
                "artifact_id": artifact_id,
                "ordinal": ordinal,
                "text": body,
            }
        )
    return chunks


def search_chunks(chunks: Iterable[dict], query: str, top_k: int = 8) -> list[dict]:
    """Rank chunks with an IDF-weighted lexical score and bounded heap."""
    query_terms = Counter(tokenize(query))
    if not query_terms:
        return []
    rows = [(chunk, Counter(tokenize(chunk.get("text", "")))) for chunk in chunks]
    if not rows:
        return []
    doc_frequency = {
        term: sum(1 for _, terms in rows if term in terms)
        for term in query_terms
    }
    total = len(rows)
    scored: list[tuple[float, int, dict]] = []
    for index, (chunk, terms) in enumerate(rows):
        length_norm = 1.0 / math.sqrt(max(1, sum(terms.values())))
        score = 0.0
        for term, query_count in query_terms.items():
            if not terms.get(term):
                continue
            idf = math.log((total + 1) / (doc_frequency[term] + 0.5)) + 1.0
            score += min(terms[term], 3) * min(query_count, 2) * idf
        score *= length_norm
        if score > 0:
            scored.append((score, -index, chunk))
    limit = max(1, min(int(top_k), 50))
    ranked = heapq.nlargest(limit, scored, key=lambda item: (item[0], item[1]))
    return [{**chunk, "score": round(score, 6)} for score, _, chunk in ranked]
