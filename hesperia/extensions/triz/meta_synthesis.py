# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Meta-area synthesis (report layer only). Never writes into domain matrix cells.
"""

from __future__ import annotations

from typing import Any


def aggregate_cross_domain_signals(domain_outputs: dict[str, Any]) -> dict[str, Any]:
    """
    Meta Area 11 (system/control) and Meta Area 12 (cross-domain) channel summaries.
    """
    contradictions = domain_outputs.get("contradictions") or []
    clusters = domain_outputs.get("innovation_clusters") or []
    narratives = domain_outputs.get("narratives") or []
    prop = domain_outputs.get("propagation_topology") or {}
    scores = [float(c.get("score", 0)) for c in contradictions if isinstance(c, dict)]
    pen = list((prop.get("contradiction_pressure") or {}).values()) if prop else []

    meta_11 = {
        "channel": "meta_area_11_system_control",
        "signal_quality": round(1.0 - (sum(scores) / max(len(scores), 1)) * 0.1 if scores else 0.0, 6),
        "contradiction_count": len(contradictions),
        "propagation_stability": round(
            sum(float(n.get("stability", 0)) for n in narratives) / max(len(narratives), 1),
            6,
        )
        if narratives
        else 0.0,
        "coverage_completeness": round(min(1.0, len(clusters) / 10.0), 6),
        "mean_contradiction_pressure": round(sum(float(x) for x in pen) / max(len(pen), 1), 6)
        if pen
        else 0.0,
    }
    top_contra = sorted(
        contradictions,
        key=lambda x: (-float(x.get("score", 0)), str(x.get("concept_a", ""))),
    )[:8]
    top_clust = sorted(
        clusters,
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )[:8]
    spill = domain_outputs.get("spillover_targets") or []
    meta_12 = {
        "channel": "meta_area_12_cross_domain",
        "strongest_contradictions": top_contra,
        "strongest_innovation_clusters": top_clust,
        "strongest_narrative_spillovers": list(spill)[:16],
    }
    return {
        "meta_area_11_equivalent": meta_11,
        "meta_area_12_equivalent": meta_12,
    }
