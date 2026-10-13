"""Build finalized iteration_segment_openai_v1 (+ messages) from a session bundle."""

from __future__ import annotations

from typing import Any

from segment import extract_iteration_segment, finalize_segment_openai_v1

from . import inspector as insp


def final_segment_for_bundle(bundle: dict[str, Any], iteration_order: int) -> dict[str, Any]:
    """Resolve iteration by numeric order; extract + Kernberg finalize."""
    current, _ = insp.resolve_iteration(bundle, str(iteration_order))
    iid = str(current.get("iteration_id", "")).strip()
    if not iid:
        raise KeyError("iteration_id missing on iteration")
    base = extract_iteration_segment(bundle, iid)
    return finalize_segment_openai_v1(base)
