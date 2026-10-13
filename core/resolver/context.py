# HESPERIA — RAD. Deterministic resolver input_context features (Ethan PO-07).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import re
from typing import Any

from core.dynamics.numeric import clamp01

_TOKEN_IN_LABEL = re.compile(r"[a-z0-9]+")


def label_token_overlap(canonical_text: str, span_start: int, span_end: int, label: str, *, window: int = 48) -> int:
    """Count label tokens that also appear in a fixed char window around the span."""
    if not label or not canonical_text:
        return 0
    lo = max(0, span_start - window)
    hi = min(len(canonical_text), span_end + window)
    chunk = canonical_text[lo:hi]
    label_tokens = set(_TOKEN_IN_LABEL.findall(label.casefold()))
    if not label_tokens:
        return 0
    chunk_tokens = set(_TOKEN_IN_LABEL.findall(chunk))
    return len(label_tokens & chunk_tokens)


def coherence_from_related(
    concept_id: str,
    concept_index: dict[str, Any],
    *,
    sibling_ids: frozenset[str],
) -> float:
    """
    Tiny deterministic coherence boost when another candidate shares ``related_concept_ids``.
    """
    meta = concept_index.get(concept_id) or {}
    related = frozenset(str(x) for x in (meta.get("related_concept_ids") or []) if x)
    if not related or not sibling_ids:
        return 0.0
    return 0.15 * float(len(related & sibling_ids))


def coherence_from_empirical(
    concept_id: str,
    sibling_ids: frozenset[str],
    *,
    dict_d_pairs: dict[tuple[str, str], float] | None = None,
) -> float:
    """
    D-derived empirical coherence (CHI-015 O4): strongest Dict D NPMI between
    ``concept_id`` and any sibling candidate, clamped to [0, 1] (negative/no-signal
    pairs contribute nothing — this is a boost, not a penalty channel).

    Isolated on purpose from :func:`coherence_from_related` (B-derived) — CHI-015
    spec §9 calls for D's contribution to be its own weighted term in
    ``score_candidate``, not bundled into ``resolver.weight_locality``.

    ``sibling_ids`` here means the CORE-D2 W0 runtime context contract's
    "deduplicated baseline-winning concept IDs from other hits in the same
    paragraph" — see :func:`resolve_paragraph_hits` in ``resolver.py``, the
    only correct way to construct this set. Passing same-hit sibling
    candidates (the ``hit.candidate_concept_ids`` alternative readings of one
    ambiguous lexical hit) here is exactly the violation W0 forbids; that
    quantity belongs only to :func:`coherence_from_related`.

    Returns 0.0 (fully inert) whenever ``dict_d_pairs`` is not supplied or
    ``resolver.coherence_empirical_weight`` is 0.0 in ``engine_constants.json``
    (the current live state) — this function existing does not change any
    live score until both are flipped.
    """
    if not dict_d_pairs or not sibling_ids:
        return 0.0
    best = 0.0
    for sib in sibling_ids:
        if sib == concept_id:
            continue
        key = (concept_id, sib) if concept_id <= sib else (sib, concept_id)
        npmi = dict_d_pairs.get(key)
        if npmi is not None and npmi > best:
            best = npmi
    return clamp01(best)


def coherence_from_empirical_traced(
    concept_id: str,
    sibling_ids: frozenset[str],
    *,
    dict_d_pairs: dict[tuple[str, str], float] | None = None,
) -> tuple[float, str | None]:
    """Same computation as :func:`coherence_from_empirical`, also returning
    which sibling concept produced the winning (strongest-positive) pair, or
    ``None`` if no positive pair was found — CORE-D2-085 empirical trace."""
    if not dict_d_pairs or not sibling_ids:
        return 0.0, None
    best = 0.0
    best_sib: str | None = None
    for sib in sibling_ids:
        if sib == concept_id:
            continue
        key = (concept_id, sib) if concept_id <= sib else (sib, concept_id)
        npmi = dict_d_pairs.get(key)
        if npmi is not None and npmi > best:
            best = npmi
            best_sib = sib
    return clamp01(best), best_sib


# --- CORE-D2 W8: paragraph-scoped context grouping ---------------------------------
#
# Deliberately duplicated (not imported from tools/dict_calibration/resolved_export.py)
# per the same runtime/build-time layering boundary core/resolver/dict_d_index.py
# already documents. This groups hits within ONE pipeline call's canonical analysis
# text into blank-line-delimited paragraphs, for empirical-context purposes only —
# it is not the calibration-time paragraph identity used for Dict D's own corpus
# export/build (a different artifact, over raw corpus source text).


def _blank_line_delimited_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []
    current_lines: list[str] = []
    for line in normalized.split("\n"):
        if line.strip():
            current_lines.append(line)
        elif current_lines:
            paragraphs.append("\n".join(current_lines))
            current_lines = []
    if current_lines:
        paragraphs.append("\n".join(current_lines))
    return paragraphs


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Character ``(start, end)`` spans for each blank-line-delimited paragraph
    in ``text``, in order. Empty/whitespace-only ``text`` returns ``[]``."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for paragraph in _blank_line_delimited_paragraphs(text):
        start = text.index(paragraph, cursor)
        end = start + len(paragraph)
        spans.append((start, end))
        cursor = end
    return spans


def paragraph_index_for_span(spans: list[tuple[int, int]], position: int) -> int:
    """Which paragraph (index into ``spans``) a character ``position`` falls in.

    Falls back to the nearest preceding paragraph for a position that lands in
    inter-paragraph whitespace (should not happen for real matched-text spans,
    which by construction sit inside non-whitespace content); falls back to 0
    if ``position`` precedes every paragraph or ``spans`` is empty.
    """
    for i, (start, end) in enumerate(spans):
        if start <= position < end:
            return i
    for i in range(len(spans) - 1, -1, -1):
        if spans[i][0] <= position:
            return i
    return 0
