# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# R1–R4 segmenters. Contract: docs/R1_R4_SEGMENTER_CONTRACT.md
from __future__ import annotations

import re
from typing import List, Tuple


def _spans_from_slices(text: str, slices: List[str]) -> List[Tuple[int, int]]:
    """Convert list of substrings to (start, end) spans. Slices must be in order, non-overlapping."""
    spans = []
    pos = 0
    for s in slices:
        idx = text.find(s, pos)
        if idx < 0:
            continue
        spans.append((idx, idx + len(s)))
        pos = idx + len(s)
    return spans


def segment_by_sentences(text: str) -> List[Tuple[int, int]]:
    """R1: Split text into sentences; return list of (start, end) spans. Heuristic: split on period/newline followed by space or end."""
    if not text.strip():
        return []
    # Split on . ! ? followed by space or end; keep the delimiter with the sentence
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    if not parts:
        return [(0, len(text))]
    spans = []
    pos = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        idx = text.find(p, pos)
        if idx < 0:
            idx = pos
        end = idx + len(p)
        spans.append((idx, end))
        pos = end
    return spans if spans else [(0, len(text))]


def segment_by_paragraphs(text: str) -> List[Tuple[int, int]]:
    """R2: Split text into paragraphs; return list of (start, end) spans. Heuristic: split on double newline."""
    if not text.strip():
        return []
    parts = re.split(r'\n\s*\n', text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return [(0, len(text))]
    # Build spans by scanning for each part
    spans = []
    pos = 0
    for p in parts:
        idx = text.find(p, pos)
        if idx < 0:
            idx = pos
        end = idx + len(p)
        spans.append((idx, end))
        pos = end
    return spans


def segment_by_chapters(text: str) -> List[Tuple[int, int]]:
    """R3: Split text into chapters; return list of (start, end) spans. Heuristic: split on ## or 'Chapter N' or # at line start."""
    if not text.strip():
        return []
    # Match ## title or # title or "Chapter N" at line start
    pattern = r'^(?:##\s+|#\s+|Chapter\s+\d+[.:\s])\s*.*$'
    lines = text.split('\n')
    starts = []
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip(), re.IGNORECASE):
            # Start of chapter: character offset
            start = sum(len(l) + 1 for l in lines[:i])
            starts.append((i, start))
    if not starts:
        return [(0, len(text))]
    spans = []
    for k, (_, start) in enumerate(starts):
        end = starts[k + 1][1] - 1 if k + 1 < len(starts) else len(text)
        if end > start:
            spans.append((start, end))
    return spans if spans else [(0, len(text))]


def segment_by_book(text: str) -> List[Tuple[int, int]]:
    """R4: One unit covering full text. Return single (0, len(text)) span."""
    if not text.strip():
        return []
    return [(0, len(text))]


def get_text_span(text: str, span: Tuple[int, int]) -> str:
    """Return substring for span (start, end)."""
    return text[span[0]:span[1]]
