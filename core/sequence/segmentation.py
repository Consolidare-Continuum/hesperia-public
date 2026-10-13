"""Deterministic segmentation (no ML)."""

from __future__ import annotations

import re

_LINE = re.compile(r"[^\n]+")


def segment_by_newlines(text: str, *, strip: bool = True) -> list[tuple[int, int, str]]:
    """
    Return list of (char_start, char_end, segment_text) for non-empty lines.
    """
    out: list[tuple[int, int, str]] = []
    for m in _LINE.finditer(text or ""):
        chunk = m.group()
        if strip:
            inner = chunk.strip()
            if not inner:
                continue
            lead = len(chunk) - len(chunk.lstrip())
            trail = len(chunk) - len(chunk.rstrip())
            s = m.start() + lead
            e = m.end() - trail
            out.append((s, e, text[s:e]))
        else:
            if chunk:
                out.append((m.start(), m.end(), chunk))
    return out
