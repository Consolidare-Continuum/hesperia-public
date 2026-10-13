# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Product-grade report dicts: policy, innovation, narrative."""

from __future__ import annotations

from typing import Any

from hesperia.extensions.triz.meta_synthesis import aggregate_cross_domain_signals


def build_contradiction_report(ctx: dict[str, Any]) -> dict[str, Any]:
    contradictions = ctx.get("contradictions") or []
    scores = [float(c.get("score", 0)) for c in contradictions if isinstance(c, dict)]
    gti = round(sum(scores) / max(len(scores), 1), 6) if scores else 0.0
    by_area: dict[int, list[float]] = {}
    for c in contradictions:
        if not isinstance(c, dict):
            continue
        for k in ("area_a", "area_b"):
            a = c.get(k)
            if a is not None and isinstance(a, int):
                by_area.setdefault(a, []).append(float(c.get("score", 0)))
    top_areas = sorted(
        [{"area": a, "tension": round(sum(v) / len(v), 6)} for a, v in by_area.items()],
        key=lambda x: (-x["tension"], x["area"]),
    )[:12]
    fam_hot = ctx.get("family_hotspots") or []
    top_fam = sorted(fam_hot, key=lambda x: (-float(x.get("hotspot_score", 0)), x.get("area_a", 0)))[:15]
    persistent = ctx.get("persistent_contradictions") or []
    triz_classes: dict[str, int] = {}
    for c in contradictions:
        if isinstance(c, dict):
            tc = str(c.get("triz_class", ""))
            triz_classes[tc] = triz_classes.get(tc, 0) + 1
    triz_list = [{"triz_class": k, "count": v} for k, v in sorted(triz_classes.items())]
    return {
        "global_tension_index": gti,
        "top_conflict_areas": top_areas,
        "top_conflict_families": top_fam,
        "persistent_contradictions": persistent,
        "triz_classes": triz_list,
    }


def build_innovation_report(ctx: dict[str, Any]) -> dict[str, Any]:
    clusters = ctx.get("innovation_clusters") or []
    scores = [float(c.get("innovation_score", 0)) for c in clusters if isinstance(c, dict)]
    ipi = round(max(scores), 6) if scores else 0.0
    top = sorted(
        clusters,
        key=lambda x: (-float(x.get("innovation_score", 0)), str(x.get("cluster_id", ""))),
    )[:20]
    rare = sorted(
        clusters,
        key=lambda x: (float(x.get("rarity", 0)), str(x.get("cluster_id", ""))),
        reverse=True,
    )[:12]
    cross = [c for c in clusters if isinstance(c, dict) and len(c.get("concepts") or []) > 4][:15]
    stab = round(
        sum(float(c.get("rarity", 0)) for c in clusters if isinstance(c, dict)) / max(len(clusters), 1),
        6,
    )
    return {
        "innovation_pressure_index": ipi,
        "top_clusters": top,
        "rare_combinations": rare,
        "cross_area_reach": cross,
        "stability": stab,
    }


def build_narrative_report(ctx: dict[str, Any]) -> dict[str, Any]:
    narratives = ctx.get("narratives") or []
    n0 = narratives[0] if narratives else {}
    mon = ctx.get("narrative_monitor") or {}
    return {
        "narrative_id": n0.get("narrative_id", "narrative_primary"),
        "penetration": round(float(n0.get("penetration", 0)), 6),
        "velocity": round(float(n0.get("velocity", 0)), 6),
        "stability": round(float(n0.get("stability", 0)), 6),
        "dominant_routes": mon.get("dominant_routes") or [],
        "blocked_areas": mon.get("blocked_areas") or [],
        "spillover_targets": mon.get("spillover_targets") or [],
    }


def build_all_reports(ctx: dict[str, Any]) -> dict[str, Any]:
    """Includes meta synthesis (report-only)."""
    rep_c = build_contradiction_report(ctx)
    rep_i = build_innovation_report(ctx)
    rep_n = build_narrative_report(ctx)
    meta = aggregate_cross_domain_signals(
        {
            "contradictions": ctx.get("contradictions"),
            "innovation_clusters": ctx.get("innovation_clusters"),
            "narratives": ctx.get("narratives"),
            "propagation_topology": ctx.get("propagation_topology"),
            "spillover_targets": (ctx.get("narrative_monitor") or {}).get("spillover_targets"),
        }
    )
    return {
        "contradiction_report": rep_c,
        "innovation_report": rep_i,
        "narrative_report": rep_n,
        "meta_synthesis": meta,
    }
