"""T03 — Extract one iteration into iteration_segment_openai_v1-shaped dict (before messages)."""

from __future__ import annotations

import copy
from typing import Any

from .constants import DISCLAIMER_FOOTER_EN, PROMPT_PACK_ID_KERNBERG_V1, SEGMENT_SCHEMA_VERSION


def _find_iteration(iterations: list[dict[str, Any]], iteration_id: str) -> dict[str, Any] | None:
    for it in iterations:
        if str(it.get("iteration_id", "")) == iteration_id:
            return it
        if str(it.get("order", "")) == iteration_id:
            return it
    for it in iterations:
        if iteration_id == f"iter_{it.get('order', -1)}":
            return it
    return None


def extract_iteration_segment(session_bundle: dict[str, Any], iteration_id: str) -> dict[str, Any]:
    """
    Slice one iteration from session_inspector_v1 (or compatible) bundle.

    Populates meta (including disclaimer_footer), iteration, parameters,
    sentences, audit. Does not attach `messages` — use `finalize_segment_openai_v1`.
    """
    meta = copy.deepcopy(session_bundle.get("meta") or {})
    meta.setdefault("run_timestamp_utc", meta.get("run_timestamp_utc") or "1970-01-01T00:00:00Z")
    meta.setdefault("disclaimer_footer", DISCLAIMER_FOOTER_EN)
    # T06 — timing / order when present on iteration
    iterations = session_bundle.get("iterations") or []
    it = _find_iteration(list(iterations), iteration_id)
    if it is None:
        raise KeyError(f"iteration not found: {iteration_id!r}")

    order = int(it.get("order", 0))
    iteration_block = {
        "iteration_id": str(it.get("iteration_id", iteration_id)),
        "order": order,
        "t_start_ms": it.get("t_start_ms"),
        "t_end_ms": it.get("t_end_ms"),
        "wall_clock_iso": it.get("wall_clock_iso"),
    }

    parameters = copy.deepcopy(it.get("parameters") or {})
    sentences = copy.deepcopy(it.get("sentences") or [])
    audit = copy.deepcopy(it.get("audit") or {})

    # T07 — module_versions / calibration on meta from session + iteration overlay
    if it.get("module_versions") is not None:
        meta.setdefault("module_versions", {}).update(it["module_versions"])
    if it.get("calibration_dict_pack") is not None:
        meta["calibration_dict_pack"] = it["calibration_dict_pack"]

    return {
        "schema_version": SEGMENT_SCHEMA_VERSION,
        "prompt_pack_id": PROMPT_PACK_ID_KERNBERG_V1,
        "meta": meta,
        "iteration": iteration_block,
        "parameters": parameters,
        "sentences": sentences,
        "audit": audit,
    }
