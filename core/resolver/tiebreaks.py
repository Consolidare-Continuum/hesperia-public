"""Stable tie-break behavior for deterministic resolver (Ethan PO-08)."""

from __future__ import annotations

from typing import Any


def break_tie(concept_ids: list[str], concept_index: dict[str, Any] | None = None) -> str:
    """
    Tie-break table (fixed order):

    1. Higher ``specificity_rank`` (from Dict B).
    2. Lexicographic ``concept_id`` (stable, deterministic).
    """
    if not concept_ids:
        raise ValueError("break_tie requires non-empty concept_ids")
    if concept_index is None:
        return sorted(concept_ids)[0]

    def sort_key(cid: str) -> tuple[int, str]:
        spec = int((concept_index.get(cid) or {}).get("specificity_rank", 0))
        return (-spec, cid)

    return sorted(concept_ids, key=sort_key)[0]

