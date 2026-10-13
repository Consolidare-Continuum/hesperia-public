# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Summary-first UI payloads (no raw graph dumps by default)."""

from __future__ import annotations

from typing import Any


def build_policy_ui_payload(triz_full: dict[str, Any], *, max_rows: int = 24) -> dict[str, Any]:
    cr = triz_full.get("reports", {}).get("contradiction_report", {})
    top = triz_full.get("topology", {}).get("family_hotspots", [])[:max_rows]
    triz_cls = cr.get("triz_classes", [])
    return {
        "section": "policy",
        "global_score": round(float(cr.get("global_tension_index", 0)), 4),
        "conflict_hotspots": [{"area_a": h.get("area_a"), "family_a": h.get("family_a"), "score": h.get("hotspot_score")} for h in top],
        "area_family_heatmap_hint": len(top),
        "triz_class_distribution": triz_cls[:16],
    }


def build_innovation_ui_payload(triz_full: dict[str, Any], *, max_rows: int = 20) -> dict[str, Any]:
    cl = sorted(
        triz_full.get("innovation_clusters", []),
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )[:max_rows]
    return {
        "section": "innovation",
        "ranked_clusters": [
            {"id": c.get("cluster_id"), "score": c.get("innovation_score"), "rarity": c.get("rarity"), "n_concepts": len(c.get("concepts") or [])}
            for c in cl
        ],
        "reach_chart": [{"id": c.get("cluster_id"), "reach": c.get("propagation_reach")} for c in cl],
        "rarity_chart": [{"id": c.get("cluster_id"), "rarity": c.get("rarity")} for c in cl],
        "persistence_markers": [],
    }


def build_narrative_ui_payload(triz_full: dict[str, Any], *, max_routes: int = 16) -> dict[str, Any]:
    nar = triz_full.get("narratives", [{}])[0]
    routes = (triz_full.get("topology", {}).get("narrative_routes") or [])[:max_routes]
    rep = triz_full.get("reports", {}).get("narrative_report", {})
    blk = rep.get("blocked_areas", [])
    spill = rep.get("spillover_targets", [])
    return {
        "section": "narrative",
        "penetration_ranking": [{"narrative_id": nar.get("narrative_id"), "penetration": nar.get("penetration")}],
        "route_graph_meta": {"steps": len(routes), "areas_touched": sorted({r.get("area") for r in routes if r.get("area") is not None})},
        "routes_preview": routes,
        "blocked_routes": blk[:12],
        "spillover_table": [{"area": a} for a in spill[:12]],
    }


def build_comparison_ui_payload(comp: dict[str, Any]) -> dict[str, Any]:
    return {
        "section": "comparison",
        "deltas": comp.get("deltas", {}),
        "emerging": comp.get("emerging_signals", [])[:16],
        "fading": comp.get("fading_signals", [])[:16],
        "overlap_summary": comp.get("common_signals", []),
        "summary": comp.get("summary_text", ""),
    }
