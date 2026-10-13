# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Compact investor-facing snapshots (controlled evidence, not full transparency)."""

from __future__ import annotations

from typing import Any


def build_investor_snapshot(
    corpus_id: str,
    report_bundle: dict[str, Any],
    *,
    product: str = "Policy Contradiction Detector",
) -> dict[str, Any]:
    rep = report_bundle.get("reports", {}).get("contradiction_report", {})
    gti = float(rep.get("global_tension_index", 0))
    top_fam = rep.get("top_conflict_families") or []
    cross_n = len([x for x in top_fam if x.get("area_a") != x.get("area_b")])
    headline = "Elevated policy tension across domains" if gti > 0.35 else "Moderate structural tension"
    if gti < 0.15:
        headline = "Low tension profile (coherent corpus)"
    return {
        "analyzed_corpus": corpus_id,
        "commercial_relevance": "Useful for media, NGOs, think tanks, and policy desks",
        "headline_signal": headline,
        "product": product,
        "supporting_metrics": {
            "cross_domain_conflicts": cross_n,
            "global_tension_score": round(gti, 4),
        },
        "what_generic_methods_miss": (
            "Keyword overlap misses typed conflict relations; unbounded graphs miss "
            "area-bounded propagation and blockage from contradiction pressure."
        ),
        "what_matters": "Structured cross-domain friction and resolution-class patterns, not raw term counts.",
        "what_was_analyzed": f"Corpus {corpus_id}: active semantic graph + HESPERIA topology-bound TRIZ layer.",
        "why_signal_found": f"Tension index {round(gti, 4)} from scored contradiction edges and family hotspots.",
    }
