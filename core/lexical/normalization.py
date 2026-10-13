"""Deterministic text normalization utilities for DLCR."""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)


class NormalizedOutput(TypedDict):
    original_text: str
    canonical_text: str
    tokens: list[str]
    token_spans: list[tuple[int, int]]
    phrase_spans: list[tuple[int, int]]


def _canonicalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text: str, max_phrase_len: int = 5) -> NormalizedOutput:
    """Return deterministic canonicalization with token and phrase spans."""
    canonical = _canonicalize(text)
    token_spans: list[tuple[int, int]] = []
    tokens: list[str] = []
    for match in TOKEN_RE.finditer(canonical):
        token_spans.append((match.start(), match.end()))
        tokens.append(match.group(0))

    phrase_spans: list[tuple[int, int]] = []
    if token_spans:
        for start_idx in range(len(token_spans)):
            for length in range(2, max_phrase_len + 1):
                end_idx = start_idx + length - 1
                if end_idx >= len(token_spans):
                    break
                phrase_spans.append((token_spans[start_idx][0], token_spans[end_idx][1]))

    return {
        "original_text": text,
        "canonical_text": canonical,
        "tokens": tokens,
        "token_spans": token_spans,
        "phrase_spans": phrase_spans
    }

