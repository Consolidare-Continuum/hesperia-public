# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Corpus-to-corpus comparison on product report payloads (deterministic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _contra_key(c: dict[str, Any]) -> tuple[str, str]:
    a, b = str(c.get("concept_a", "")), str(c.get("concept_b", ""))
    return (a, b) if a <= b else (b, a)


def _hotspot_key(h: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(h.get("area_a", -1)),
        int(h.get("family_a", -1)),
        int(h.get("area_b", -1)),
        int(h.get("family_b", -1)),
    )


def compare_policy_reports(report_a: dict[str, Any], report_b: dict[str, Any]) -> dict[str, Any]:
    ta = float(report_a.get("global_tension_score", 0))
    tb = float(report_b.get("global_tension_score", 0))
    ca = { _contra_key(x) for x in (report_a.get("top_cross_domain_conflicts") or []) if isinstance(x, dict) }
    cb = { _contra_key(x) for x in (report_b.get("top_cross_domain_conflicts") or []) if isinstance(x, dict) }
    ha = { _hotspot_key(x) for x in (report_a.get("top_conflict_clusters") or []) if isinstance(x, dict) }
    hb = { _hotspot_key(x) for x in (report_b.get("top_conflict_clusters") or []) if isinstance(x, dict) }
    return {
        "hotspot_overlap": len(ha & hb),
        "hotspot_only_b": len(hb - ha),
        "new_contradictions": sorted(cb - ca),
        "resolved_contradictions": sorted(ca - cb),
        "tension_delta": round(tb - ta, 6),
    }


def _cluster_sig(c: dict[str, Any]) -> str:
    concepts = sorted(c.get("concepts") or [])
    return "|".join(concepts)[:256]


def compare_innovation_reports(report_a: dict[str, Any], report_b: dict[str, Any]) -> dict[str, Any]:
    sa = {_cluster_sig(x) for x in (report_a.get("strongest_clusters") or report_a.get("rare_clusters") or [])}
    sb = {_cluster_sig(x) for x in (report_b.get("strongest_clusters") or report_b.get("rare_clusters") or [])}
    ra = float(report_a.get("innovation_pressure_score", 0))
    rb = float(report_b.get("innovation_pressure_score", 0))
    reach_a = [float(x.get("reach") or 0) for x in (report_a.get("spread_summary") or [])]
    reach_b = [float(x.get("reach") or 0) for x in (report_b.get("spread_summary") or [])]
    ma = sum(reach_a) / max(len(reach_a), 1)
    mb = sum(reach_b) / max(len(reach_b), 1)
    persistence = len(sa & sb)
    return {
        "cluster_persistence_count": persistence,
        "new_clusters": sorted(sb - sa)[:32],
        "novelty_decay": round(max(0.0, ra - rb), 6),
        "reach_delta": round(mb - ma, 6),
    }


def compare_narrative_reports(report_a: dict[str, Any], report_b: dict[str, Any]) -> dict[str, Any]:
    na = (report_a.get("narratives") or [{}])[0]
    nb = (report_b.get("narratives") or [{}])[0]
    pa, pb = float(na.get("penetration", 0)), float(nb.get("penetration", 0))
    routes_a = {tuple(r.get("area") for r in (report_a.get("top_routes") or []) if r.get("area") is not None)}
    routes_b = {tuple(r.get("area") for r in (report_b.get("top_routes") or []) if r.get("area") is not None)}
    def _blk(rep: dict[str, Any]) -> set[int]:
        s: set[int] = set()
        for x in rep.get("blocked_routes") or []:
            if isinstance(x, dict) and x.get("area") is not None:
                s.add(int(x["area"]))
        return s

    ba, bb = _blk(report_a), _blk(report_b)
    sa = set(report_a.get("spillover_targets") or [])
    sb = set(report_b.get("spillover_targets") or [])
    return {
        "blockage_shift": {"only_a": sorted(ba - bb), "only_b": sorted(bb - ba)},
        "penetration_delta": round(pb - pa, 6),
        "route_shift": {"overlap": len(routes_a & routes_b), "only_b_count": len(routes_b - routes_a)},
        "spillover_change": {"only_b": sorted(sb - sa), "only_a": sorted(sa - sb)},
    }


@dataclass
class ComparisonReport:
    left_corpus_id: str
    right_corpus_id: str
    product_sku: str
    deltas: dict[str, Any]
    common_signals: list[str]
    emerging_signals: list[str]
    fading_signals: list[str]
    summary_text: str = ""


def build_comparison_summary(
    left_id: str,
    right_id: str,
    product: str,
    d: dict[str, Any],
) -> str:
    parts = [f"Compared with {left_id}, {right_id} shows"]
    if product == "policy":
        td = float(d.get("tension_delta", 0))
        parts.append(f"tension {'higher' if td > 0.02 else 'lower' if td < -0.02 else 'similar'} cross-domain profile (delta {td:+.2f}).")
        if d.get("new_contradictions"):
            parts.append(f"{len(d['new_contradictions'])} new contradiction loci.")
        if d.get("resolved_contradictions"):
            parts.append(f"{len(d['resolved_contradictions'])} prior loci absent.")
    elif product == "innovation":
        nc = d.get("new_clusters") or []
        if nc:
            parts.append(f"{len(nc)} new innovation cluster(s).")
        parts.append(f"reach delta {float(d.get('reach_delta', 0)):+.3f}.")
    else:
        parts.append(f"penetration delta {float(d.get('penetration_delta', 0)):+.3f}.")
        sc = d.get("spillover_change") or {}
        if sc.get("only_b"):
            parts.append(f"spillover into areas {sc['only_b'][:4]}.")
    return " ".join(parts)


def compare_reports_unified(
    left_corpus_id: str,
    right_corpus_id: str,
    product_sku: str,
    report_a: dict[str, Any],
    report_b: dict[str, Any],
    *,
    product_kind: str,
) -> ComparisonReport:
    if product_kind == "policy":
        deltas = compare_policy_reports(report_a, report_b)
    elif product_kind == "innovation":
        deltas = compare_innovation_reports(report_a, report_b)
    else:
        deltas = compare_narrative_reports(report_a, report_b)

    emerging: list[str] = []
    fading: list[str] = []
    common: list[str] = []
    if product_kind == "policy":
        emerging = [f"contradiction:{a}|{b}" for a, b in (deltas.get("new_contradictions") or [])[:12]]
        fading = [f"contradiction:{a}|{b}" for a, b in (deltas.get("resolved_contradictions") or [])[:12]]
        common = [f"hotspot_overlap:{deltas.get('hotspot_overlap', 0)}"]
    elif product_kind == "innovation":
        emerging = [f"cluster:{x}" for x in (deltas.get("new_clusters") or [])[:8]]
        common = [f"persisted_clusters:{deltas.get('cluster_persistence_count', 0)}"]
    else:
        emerging = [f"spillover_area:{a}" for a in (deltas.get("spillover_change") or {}).get("only_b", [])[:8]]

    st = build_comparison_summary(left_corpus_id, right_corpus_id, product_kind, deltas)
    return ComparisonReport(
        left_corpus_id=left_corpus_id,
        right_corpus_id=right_corpus_id,
        product_sku=product_sku,
        deltas=deltas,
        common_signals=common,
        emerging_signals=emerging,
        fading_signals=fading,
        summary_text=st,
    )
