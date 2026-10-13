# HESPERIA — FPF-BUII climb + gap_detect.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any

from sphere.fpf_inspect.constants import CLIMB_ORDER
from sphere.fpf_inspect.probe import gaps_from_slice, probe
from sphere.fpf_inspect.schemas import make_gap_report


def inspect_climb(
    analyze_result: dict[str, Any] | None,
    *,
    stop_on_first_gap: bool = True,
    layers: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """
    Climb layers bottom-up. Returns {slices, gap_report}.
    When stop_on_first_gap, stops after the first layer that emits any gap
    (missing_evidence or provisional_adr). L0 pin/analyze gaps always counted.
    """
    order = layers or CLIMB_ORDER
    slices: list[dict[str, Any]] = []
    all_gaps: list[dict[str, Any]] = []
    lowest: str | None = None

    for layer_id in order:
        slice_ = probe(layer_id, analyze_result)
        slices.append(slice_)
        layer_gaps = gaps_from_slice(slice_)
        if layer_gaps:
            if lowest is None:
                lowest = layer_id
            all_gaps.extend(layer_gaps)
            if stop_on_first_gap:
                break

    report = make_gap_report(
        gaps=all_gaps,
        analyze_result=analyze_result,
        lowest_failed_layer=lowest or "none",
    )
    return {"slices": slices, "gap_report": report}


def gap_detect(analyze_result: dict[str, Any] | None) -> dict[str, Any]:
    """Full climb without early stop — complete GapReport."""
    return inspect_climb(analyze_result, stop_on_first_gap=False)["gap_report"]
