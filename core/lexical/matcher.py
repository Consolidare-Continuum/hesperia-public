"""Phrase-first deterministic matcher for Dict A entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


MATCH_RANK = {"exact": 0, "phrase": 1, "lemma": 2, "stem": 3, "pattern": 4}


@dataclass(frozen=True)
class LexicalHit:
    entry_id: str
    matched_text: str
    span_start: int
    span_end: int
    match_type: str
    candidate_concept_ids: list[str]
    priority: int


def _sort_key(hit: LexicalHit) -> tuple[int, int, int, int]:
    return (
        hit.span_start,
        -(hit.span_end - hit.span_start),  # longest span first
        MATCH_RANK.get(hit.match_type, 99),
        -hit.priority
    )


def _collect_negative_blocks(canonical_text: str, entries: list[dict]) -> list[tuple[int, int]]:
    """Spans that must not produce lexical hits (Ethan TFP RU negative layer)."""
    blocks: list[tuple[int, int]] = []
    for entry in entries:
        neg = entry.get("negative_patterns") or []
        if not neg:
            continue
        needle = entry.get("normalized_form")
        if not needle:
            continue
        start = canonical_text.find(needle)
        while start >= 0:
            end = start + len(needle)
            blocks.append((start, end))
            start = canonical_text.find(needle, start + 1)
    return blocks


def _overlaps_block(span_start: int, span_end: int, blocks: list[tuple[int, int]]) -> bool:
    for bs, be in blocks:
        if span_start < be and bs < span_end:
            return True
    return False


def _diversity_capped(
    accepted: list[LexicalHit],
    max_accepted: int,
    diversity_key: Callable[[LexicalHit], str],
) -> tuple[list[LexicalHit], list[LexicalHit]]:
    """Round-robin across ``diversity_key`` groups (each in position order), then
    re-sort survivors back to document order -- callers rely on ``accepted`` being
    in span order (e.g. sequential-association boosts keyed on textual recency).
    """
    groups: dict[str, list[LexicalHit]] = {}
    group_order: list[str] = []
    for hit in accepted:
        key = diversity_key(hit)
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(hit)

    selected: list[LexicalHit] = []
    while len(selected) < max_accepted:
        progressed = False
        for key in group_order:
            if len(selected) >= max_accepted:
                break
            queue = groups[key]
            if queue:
                selected.append(queue.pop(0))
                progressed = True
        if not progressed:
            break

    selected_ids = {id(h) for h in selected}
    overflow = [h for h in accepted if id(h) not in selected_ids]
    selected.sort(key=_sort_key)
    return selected, overflow


def match_dict_a(
    canonical_text: str,
    entries: list[dict],
    *,
    max_accepted: int | None = None,
    diversity_key: Callable[[LexicalHit], str] | None = None,
) -> tuple[list[LexicalHit], list[LexicalHit]]:
    """
    Find deterministic lexical hits and reject overlapping lower-priority hits.

    PO-03: sort prefers **longest span** at same start, then stronger ``match_type``.
    PO-04: optional ``max_accepted`` caps accepted hits (overflow appended to rejected).
    PO-31: optional ``diversity_key`` makes the cap group-aware -- round-robins across
    groups (in position order within each) instead of a flat position-order cut, so a
    group that only appears late in the text still gets a fair share of the budget.
    Without it, behavior is unchanged: a flat slice by document position. Selected hits
    are always returned in document order regardless of which path was used.
    Entries with non-empty ``negative_patterns`` only contribute **blocked spans** (no LexicalHit).
    """
    blocks = _collect_negative_blocks(canonical_text, entries)
    candidates: list[LexicalHit] = []
    for entry in entries:
        if entry.get("negative_patterns"):
            continue
        needle = entry.get("normalized_form")
        if not needle:
            continue
        start = canonical_text.find(needle)
        while start >= 0:
            end = start + len(needle)
            if _overlaps_block(start, end, blocks):
                start = canonical_text.find(needle, start + 1)
                continue
            candidates.append(
                LexicalHit(
                    entry_id=entry["entry_id"],
                    matched_text=needle,
                    span_start=start,
                    span_end=end,
                    match_type=entry["match_type"],
                    candidate_concept_ids=list(entry.get("candidate_concept_ids") or []),
                    priority=entry.get("priority", 0)
                )
            )
            start = canonical_text.find(needle, start + 1)

    candidates.sort(key=_sort_key)
    accepted: list[LexicalHit] = []
    rejected: list[LexicalHit] = []

    for hit in candidates:
        overlap = False
        for selected in accepted:
            if hit.span_start < selected.span_end and selected.span_start < hit.span_end:
                overlap = True
                break
        if overlap:
            rejected.append(hit)
        else:
            accepted.append(hit)

    if max_accepted is not None and max_accepted >= 0 and len(accepted) > max_accepted:
        if diversity_key is not None:
            accepted, overflow = _diversity_capped(accepted, max_accepted, diversity_key)
        else:
            overflow = accepted[max_accepted:]
            accepted = accepted[:max_accepted]
        rejected.extend(overflow)

    return accepted, rejected

