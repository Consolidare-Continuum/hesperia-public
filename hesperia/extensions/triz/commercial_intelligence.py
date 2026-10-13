# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Decision-intelligence products derived from TRIZ atomic outputs.
Policy / innovation / narrative / system stability / comparative / monitoring schemas.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from hesperia.extensions.triz.direct_outputs import TRIZDirectMetrics, compare_triz_direct
from hesperia.extensions.triz.models import TRIZSignals


def _r6(x: float) -> float:
    return round(min(1.0, max(0.0, float(x))), 6)


def _family_conflict_density(dm: TRIZDirectMetrics) -> list[dict[str, Any]]:
    acc: dict[int, float] = defaultdict(float)
    cnt: dict[int, int] = defaultdict(int)
    for h in dm.contradiction_hotspots:
        fid = int(h.get("family_id", -1))
        if fid < 0:
            continue
        acc[fid] += float(h.get("hotspot_score", 0.0))
        cnt[fid] += 1
    out = [
        {
            "family_id": f,
            "conflict_density": _r6(acc[f] / max(cnt[f], 1)),
            "hotspot_mass": _r6(acc[f]),
        }
        for f in sorted(acc.keys())
    ]
    out.sort(key=lambda x: (-x["conflict_density"], x["family_id"]))
    return out[:64]


def build_commercial_intelligence_bundle(sig: TRIZSignals) -> dict[str, Any]:
    """
    Full commercial derivative layer from one TRIZSignals (+ direct_metrics).
    Deterministic ordering; numeric fields rounded to 6 decimals.
    """
    dm = sig.direct_metrics
    if dm is None:
        return _empty_commercial_bundle()

    scores = dm.contradiction_scores
    policy_tension = _r6(sum(scores) / len(scores)) if scores else 0.0
    policy_coherence = _r6(1.0 - dm.contradiction_density)

    detail_by_cid = {d["cluster_id"]: d for d in dm.innovation_clusters_detail}
    radar = []
    for cl in sorted(sig.innovation_clusters, key=lambda x: (-x.innovation_score, x.cluster_id)):
        det = detail_by_cid.get(cl.cluster_id, {})
        radar.append(
            {
                "cluster_id": cl.cluster_id,
                "cluster_score": _r6(cl.innovation_score),
                "cluster_reach": int(det.get("cluster_reach", 0)),
                "cluster_rarity_score": _r6(float(det.get("cluster_rarity_score", 0.0))),
                "concept_count": int(det.get("concept_count", len(cl.concepts))),
            }
        )

    cross_domain_ops = [r for r in radar if r["cluster_reach"] >= 2]
    cross_domain_ops.sort(key=lambda x: (-x["cluster_score"], x["cluster_id"]))

    idea_novelty = [
        {
            "cluster_id": r["cluster_id"],
            "idea_novelty_score": _r6(
                float(r["cluster_rarity_score"]) * min(1.0, r["cluster_reach"] / 12.0)
            ),
        }
        for r in radar
    ]

    pairs = [
        {
            "concept_a": c.concept_a,
            "concept_b": c.concept_b,
            "contradiction_score": _r6(c.score),
            "triz_class": c.triz_class,
            "area_a": c.coord_a.area_id,
            "area_b": c.coord_b.area_id,
        }
        for c in sorted(sig.contradictions, key=lambda x: (-x.score, x.concept_a, x.concept_b))
    ]

    coupling_map = {
        k: _r6(v)
        for k, v in sorted(dm.domain_coupling.items())
        if k != "aggregate_cross_area_edge_rate"
    }

    unstable = bool(
        dm.contradiction_count >= 5
        and dm.cross_area_contradiction_rate > 0.25
        and dm.contradiction_density > 0.08
    )

    core_signals = {
        "policy_tension_index": policy_tension,
        "policy_coherence_score": policy_coherence,
        "innovation_radar_peak_score": _r6(dm.innovation_score),
        "innovation_pressure_index": _r6(dm.innovation_pressure),
        "narrative_penetration_score": _r6(dm.narrative_penetration),
        "narrative_spillover_index": _r6(dm.spillover_strength),
        "system_tension_index": _r6(dm.semantic_pressure),
        "cross_area_contradiction_rate": _r6(dm.cross_area_contradiction_rate),
        "activation_energy": _r6(dm.activation_energy),
    }

    return {
        "schema_version": "commercial_intelligence_v1",
        "core_signals": core_signals,
        "policy_contradiction_products": {
            "policy_tension_index": policy_tension,
            "policy_coherence_score": policy_coherence,
            "policy_conflict_map": {
                "hotspot_ranking": list(dm.contradiction_hotspots)[:48],
                "family_conflict_density": _family_conflict_density(dm),
                "cross_area_conflicts": {
                    "cross_area_contradiction_rate": _r6(dm.cross_area_contradiction_rate),
                    "estimated_cross_area_pairs": int(
                        round(dm.cross_area_contradiction_rate * max(dm.contradiction_count, 1))
                    ),
                },
            },
            "regulatory_conflict_detector": {
                "incompatible_regulation_pairs_count": dm.contradiction_count,
                "contradiction_pairs": pairs[:250],
            },
        },
        "innovation_intelligence_products": {
            "innovation_radar": {
                "cluster_ranking": radar[:40],
                "cluster_count": len(radar),
            },
            "innovation_pressure_index": _r6(dm.innovation_pressure),
            "cross_domain_opportunity_detector": {
                "bridging_clusters": cross_domain_ops[:24],
                "bridge_count": len(cross_domain_ops),
            },
            "idea_novelty_scores": idea_novelty[:40],
        },
        "narrative_intelligence_products": {
            "narrative_penetration_score": _r6(dm.narrative_penetration),
            "narrative_propagation_speed": _r6(dm.propagation_velocity),
            "narrative_spillover_index": _r6(dm.spillover_strength),
            "narrative_stability_score": _r6(dm.narrative_stability),
            "narrative_route_length": int(dm.narrative_route_length),
        },
        "system_stability_products": {
            "system_tension_index": _r6(dm.semantic_pressure),
            "domain_coupling_map": coupling_map,
            "aggregate_cross_area_edge_rate": _r6(
                float(dm.domain_coupling.get("aggregate_cross_area_edge_rate", 0.0))
            ),
            "structural_instability_detector": {
                "unstable_structure_flag": unstable,
                "contradiction_density": _r6(dm.contradiction_density),
                "contradiction_cluster_count": dm.contradiction_count,
            },
        },
        "comparative_intelligence_products": {
            "note": "Apply compare_triz_corpora(previous_dm, current_dm) for strategy_divergence, innovation_momentum, narrative_shift.",
            "compare_endpoint": "/api/v1/triz/compare",
        },
        "monitoring_products_schema": {
            "narrative_monitoring_dashboard": {
                "tracks": ["penetration", "propagation_velocity", "narrative_stability"],
                "series": "time_series_of_core_signals",
            },
            "policy_evolution_tracker": {
                "tracks": ["contradiction_density", "policy_coherence_score", "policy_tension_index"],
            },
            "innovation_landscape_monitor": {
                "tracks": ["innovation_cluster_count", "innovation_pressure_index", "cluster_radar_peaks"],
            },
        },
    }


def _empty_commercial_bundle() -> dict[str, Any]:
    z = _r6(0.0)
    core = {
        "policy_tension_index": z,
        "policy_coherence_score": _r6(1.0),
        "innovation_radar_peak_score": z,
        "innovation_pressure_index": z,
        "narrative_penetration_score": z,
        "narrative_spillover_index": z,
        "system_tension_index": z,
        "cross_area_contradiction_rate": z,
        "activation_energy": z,
    }
    return {
        "schema_version": "commercial_intelligence_v1",
        "core_signals": core,
        "policy_contradiction_products": {},
        "innovation_intelligence_products": {},
        "narrative_intelligence_products": {},
        "system_stability_products": {},
        "comparative_intelligence_products": {
            "note": "Requires two corpus snapshots; use compare_triz_corpora.",
        },
        "monitoring_products_schema": {
            "narrative_monitoring_dashboard": {"tracks": ["penetration", "propagation_velocity", "stability"]},
            "policy_evolution_tracker": {"tracks": ["contradiction_density", "policy_coherence"]},
            "innovation_landscape_monitor": {"tracks": ["cluster_count", "innovation_pressure"]},
        },
    }


def commercial_intelligence_to_dict(sig: TRIZSignals) -> dict[str, Any]:
    return build_commercial_intelligence_bundle(sig)


def compare_triz_corpora(
    previous: TRIZDirectMetrics,
    current: TRIZDirectMetrics,
) -> dict[str, Any]:
    """Strategy divergence, innovation momentum, narrative shift (two documents / corpora)."""
    base = compare_triz_direct(previous, current)
    return {
        "schema_version": "comparative_intelligence_v1",
        "strategy_divergence_score": base["contradiction_delta"],
        "innovation_momentum_index": base["innovation_delta"],
        "narrative_shift_detector": base["narrative_shift"],
        "cluster_emergence_rate": base["cluster_emergence_rate"],
        "raw_deltas": base,
    }


def extract_core_commercial_signals(triz_payload: dict[str, Any]) -> dict[str, Any]:
    """From analyze response `triz` object: return core_signals only."""
    ci = triz_payload.get("commercial_intelligence") or {}
    if isinstance(ci, dict) and ci.get("core_signals"):
        return dict(ci["core_signals"])
    return {}


def extract_product_slice(triz_payload: dict[str, Any], product: str) -> dict[str, Any]:
    """product in policy | innovation | narrative | system | comparative."""
    ci = triz_payload.get("commercial_intelligence") or {}
    key = {
        "policy": "policy_contradiction_products",
        "innovation": "innovation_intelligence_products",
        "narrative": "narrative_intelligence_products",
        "system": "system_stability_products",
        "comparative": "comparative_intelligence_products",
    }.get(product, "")
    return dict(ci.get(key, {})) if key else {}
