# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""SKU-tagged export bundles for the three commercial products."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from hesperia.product.schemas.innovation_radar_schema import InnovationRadarReport
from hesperia.product.schemas.narrative_monitor_schema import NarrativeMonitorReport
from hesperia.product.schemas.policy_detector_schema import PolicyDetectorReport
from hesperia.product.summary_writer import apply_summaries
from hesperia.product.triz_metric_catalog import INTERNAL_TO_PRODUCT, product_name

PRODUCT_SKUS = {
    "policy_detector": "HSP-TRIZ-P1",
    "innovation_radar": "HSP-TRIZ-I1",
    "narrative_monitor": "HSP-TRIZ-N1",
}


def _iso_ts() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_policy_detector_report(
    corpus_id: str,
    triz_full: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> PolicyDetectorReport:
    cr = triz_full.get("reports", {}).get("contradiction_report", {})
    clusters = cr.get("top_conflict_families") or triz_full.get("topology", {}).get("family_hotspots", [])
    cross = [c for c in triz_full.get("contradictions", []) if not c.get("same_area")]
    triz = cr.get("triz_classes") or []
    gti = float(cr.get("global_tension_index", 0))
    cs = (triz_full.get("commercial_intelligence") or {}).get("core_signals") or {}
    if cs.get("policy_tension_index") is not None:
        gti = float(cs["policy_tension_index"])
    return PolicyDetectorReport(
        corpus_id=corpus_id,
        generated_at=generated_at or _iso_ts(),
        global_tension_score=round(min(1.0, max(0.0, gti)), 6),
        top_conflict_clusters=list(clusters)[:20],
        top_cross_domain_conflicts=sorted(
            cross,
            key=lambda x: (-float(x.get("score", 0)), str(x.get("concept_a", ""))),
        )[:20],
        dominant_triz_patterns=list(triz),
    )


def build_innovation_radar_report(
    corpus_id: str,
    triz_full: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> InnovationRadarReport:
    ir = triz_full.get("reports", {}).get("innovation_report", {})
    clusters = triz_full.get("innovation_clusters", [])
    rare = ir.get("rare_combinations") or sorted(
        clusters,
        key=lambda x: float(x.get("rarity", 0)),
        reverse=True,
    )[:15]
    strong = ir.get("top_clusters") or sorted(
        clusters,
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )[:15]
    spread = [{"cluster_id": c.get("cluster_id"), "reach": c.get("propagation_reach")} for c in strong]
    ipi = float(ir.get("innovation_pressure_index", 0))
    cs = (triz_full.get("commercial_intelligence") or {}).get("core_signals") or {}
    if cs.get("innovation_pressure_index") is not None:
        ipi = float(cs["innovation_pressure_index"])
    return InnovationRadarReport(
        corpus_id=corpus_id,
        generated_at=generated_at or _iso_ts(),
        innovation_pressure_score=round(min(1.0, max(0.0, ipi)), 6),
        rare_clusters=list(rare)[:20],
        strongest_clusters=list(strong)[:20],
        spread_summary=spread,
    )


def build_narrative_monitor_report(
    corpus_id: str,
    triz_full: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> NarrativeMonitorReport:
    nr = triz_full.get("reports", {}).get("narrative_report", {})
    top = triz_full.get("topology", {}).get("narrative_routes", [])
    paths = triz_full.get("topology", {}).get("strongest_paths", [])
    blocked = [
        {"area": a, "label": product_name("contradiction_pressure")}
        for a in (nr.get("blocked_areas") or [])
    ]
    spill = [{"area": a} for a in (nr.get("spillover_targets") or [])]
    stab = [{"metric": product_name("stability"), "value": n.get("stability")} for n in triz_full.get("narratives", [])]
    return NarrativeMonitorReport(
        corpus_id=corpus_id,
        generated_at=generated_at or _iso_ts(),
        narratives=list(triz_full.get("narratives", [])),
        top_routes=list(top)[:30],
        blocked_routes=blocked,
        spillovers=spill,
        stability_summary=stab,
    )


def build_policy_package(triz_full: dict[str, Any], corpus_id: str) -> dict[str, Any]:
    r = build_policy_detector_report(corpus_id, triz_full)
    apply_summaries(r, None, None)
    ci = triz_full.get("commercial_intelligence") or {}
    pol = ci.get("policy_contradiction_products") or {}
    return {
        "sku": PRODUCT_SKUS["policy_detector"],
        "product_metrics": {product_name("contradiction_score"): r.global_tension_score},
        "report": asdict(r),
        "exports": {
            "tension_hotspots": triz_full.get("topology", {}).get("area_hotspots", []),
            "triz_resolution_classes": r.dominant_triz_patterns,
            "policy_tension_index": (ci.get("core_signals") or {}).get("policy_tension_index"),
            "policy_coherence_score": pol.get("policy_coherence_score"),
            "policy_conflict_map": pol.get("policy_conflict_map"),
        },
    }


def build_innovation_package(triz_full: dict[str, Any], corpus_id: str) -> dict[str, Any]:
    r = build_innovation_radar_report(corpus_id, triz_full)
    apply_summaries(None, r, None)
    ci = triz_full.get("commercial_intelligence") or {}
    inn = ci.get("innovation_intelligence_products") or {}
    return {
        "sku": PRODUCT_SKUS["innovation_radar"],
        "product_metrics": {product_name("innovation_score"): r.innovation_pressure_score},
        "report": asdict(r),
        "exports": {
            "rare_concept_clusters": r.rare_clusters,
            "reach_stability": {
                "reach": [s.get("reach") for s in r.spread_summary],
                "stability": triz_full.get("reports", {})
                .get("innovation_report", {})
                .get("stability"),
            },
            "innovation_radar": inn.get("innovation_radar"),
            "cross_domain_opportunities": inn.get("cross_domain_opportunity_detector"),
        },
    }


def build_narrative_package(triz_full: dict[str, Any], corpus_id: str) -> dict[str, Any]:
    r = build_narrative_monitor_report(corpus_id, triz_full)
    apply_summaries(None, None, r)
    nar = (triz_full.get("commercial_intelligence") or {}).get("narrative_intelligence_products") or {}
    return {
        "sku": PRODUCT_SKUS["narrative_monitor"],
        "product_metrics": {
            product_name("propagation_penetration"): (
                float(r.narratives[0].get("penetration", 0)) if r.narratives else 0.0
            ),
        },
        "report": asdict(r),
        "exports": {
            "penetration_report": r.narratives,
            "route_map": r.top_routes,
            "blockage_map": r.blocked_routes,
            "spillover_summary": r.spillovers,
            "narrative_intelligence": nar,
        },
    }


def package_to_json(package: dict[str, Any]) -> str:
    return json.dumps(package, sort_keys=True, indent=2)
