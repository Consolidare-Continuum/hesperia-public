# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Human analyst review bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ReviewerFeedback:
    run_id: str
    reviewer_id: str
    approved: bool
    notes: str
    flagged_signals: list[str]


def build_review_pack(
    triz_full: dict[str, Any],
    package: dict[str, Any],
    *,
    corpus_id: str,
    run_id: str,
    limitations_note: str | None = None,
) -> dict[str, Any]:
    rep = package.get("report", {})
    contra = sorted(
        triz_full.get("contradictions", []),
        key=lambda x: (-float(x.get("score", 0)), str(x.get("concept_a", ""))),
    )[:20]
    pairs = [{"a": c.get("concept_a"), "b": c.get("concept_b"), "score": c.get("score")} for c in contra]
    areas = set()
    for c in contra:
        for k in ("area_a", "area_b"):
            if c.get(k) is not None:
                areas.add(int(c[k]))
    fams = set()
    for c in contra:
        for k in ("family_a", "family_b"):
            if c.get(k) is not None:
                fams.add(int(c[k]))
    return {
        "corpus_id": corpus_id,
        "limitations_note": limitations_note
        or "Signal analytics only; see TRIZ_LIMITATIONS.md. Does not prove truth or replace expert judgment.",
        "product_summary": rep.get("summary_text", ""),
        "run_id": run_id,
        "supporting_metrics": {
            "sku": package.get("sku"),
            "tension_or_pressure": rep.get("global_tension_score") or rep.get("innovation_pressure_score"),
        },
        "top_affected_areas": sorted(areas)[:24],
        "top_affected_families": sorted(fams)[:32],
        "top_contributing_concept_pairs": pairs,
        "top_signals": (rep.get("top_conflict_clusters") or rep.get("strongest_clusters") or [])[:12],
    }
