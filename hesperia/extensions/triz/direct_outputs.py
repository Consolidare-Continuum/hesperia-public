# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Atomic TRIZ outputs: numeric / categorical / structural metrics (deterministic).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from hesperia.extensions.triz.contradiction_engine import CONFLICT_TYPES
from hesperia.extensions.triz.models import ConceptActivation, ConceptRelation, ContradictionSignal, InnovationCluster

TRIZ_CLASS_KEYS = (
    "segmentation",
    "counterbalance",
    "parameter_change",
    "dynamic_adaptation",
)


def _r6(x: float) -> float:
    return round(float(x), 6)


@dataclass
class TRIZDirectMetrics:
    """Single deterministic bundle of direct TRIZ measurements."""

    contradiction_count: int = 0
    contradiction_density: float = 0.0
    contradiction_scores: list[float] = field(default_factory=list)
    cross_area_contradiction_rate: float = 0.0
    triz_class_distribution: dict[str, float] = field(default_factory=dict)
    contradiction_hotspots: list[dict[str, Any]] = field(default_factory=list)
    innovation_score: float = 0.0
    innovation_score_mean: float = 0.0
    innovation_cluster_count: int = 0
    innovation_clusters_detail: list[dict[str, Any]] = field(default_factory=list)
    innovation_pressure: float = 0.0
    narrative_penetration: float = 0.0
    propagation_velocity: float = 0.0
    spillover_strength: float = 0.0
    narrative_stability: float = 0.0
    narrative_route_length: int = 0
    area_activation: dict[str, float] = field(default_factory=dict)
    family_activation: dict[str, float] = field(default_factory=dict)
    hex_activation: dict[str, float] = field(default_factory=dict)
    domain_coupling: dict[str, float] = field(default_factory=dict)
    semantic_pressure: float = 0.0
    activation_energy: float = 0.0
    propagation_resistance: float = 0.0
    concept_mass: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradiction_count": int(self.contradiction_count),
            "contradiction_density": _r6(self.contradiction_density),
            "contradiction_scores": [_r6(s) for s in self.contradiction_scores],
            "cross_area_contradiction_rate": _r6(self.cross_area_contradiction_rate),
            "triz_class_distribution": {k: _r6(v) for k, v in sorted(self.triz_class_distribution.items())},
            "contradiction_hotspots": list(self.contradiction_hotspots),
            "innovation_score": _r6(self.innovation_score),
            "innovation_score_mean": _r6(self.innovation_score_mean),
            "innovation_cluster_count": int(self.innovation_cluster_count),
            "innovation_clusters_detail": list(self.innovation_clusters_detail),
            "innovation_pressure": _r6(self.innovation_pressure),
            "narrative_penetration": _r6(self.narrative_penetration),
            "propagation_velocity": _r6(self.propagation_velocity),
            "spillover_strength": _r6(self.spillover_strength),
            "narrative_stability": _r6(self.narrative_stability),
            "narrative_route_length": int(self.narrative_route_length),
            "area_activation": {k: _r6(v) for k, v in sorted(self.area_activation.items(), key=lambda x: int(x[0]))},
            "family_activation": {k: _r6(v) for k, v in sorted(self.family_activation.items(), key=lambda x: int(x[0]))},
            "hex_activation": {k: _r6(v) for k, v in sorted(self.hex_activation.items(), key=lambda x: int(x[0]))},
            "domain_coupling": {k: _r6(v) for k, v in sorted(self.domain_coupling.items())},
            "semantic_pressure": _r6(self.semantic_pressure),
            "activation_energy": _r6(self.activation_energy),
            "propagation_resistance": _r6(self.propagation_resistance),
            "concept_mass": _r6(self.concept_mass),
        }


def _concept_area(act: ConceptActivation) -> int:
    a = int(act.coordinate.area_id)
    return a if 0 <= a <= 11 else -1


def _narrative_route_length(
    adjacency: dict[int, list[int]],
    base: dict[int, float],
    final: dict[int, float],
    *,
    thr: float = 0.05,
) -> int:
    seed = max(range(12), key=lambda i: base.get(i, 0.0))
    if base.get(seed, 0.0) < 1e-9:
        return 0
    targets = {i for i in range(12) if final.get(i, 0.0) >= thr}
    if not targets:
        return 0
    from collections import deque

    dist: dict[int, int] = {seed: 0}
    q = deque([seed])
    while q:
        u = q.popleft()
        for v in adjacency.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return max(dist.get(t, 0) for t in targets)


def build_triz_direct_metrics(
    activations: list[ConceptActivation],
    relations: list[ConceptRelation],
    topology_adjacency: dict[int, list[int]],
    contradictions: list[ContradictionSignal],
    innovation_clusters: list[InnovationCluster],
    narratives: list[Any],
    *,
    propagation_history: list[dict[int, float]],
    final_propagated: dict[int, float],
    propagation_steps: int,
    damping: float,
    family_count: int,
    area_activation_base: dict[int, float],
) -> TRIZDirectMetrics:
    total_rel = max(len(relations), 1)
    conflict_edges = sum(
        1 for r in relations if (r.relation_type or "").strip().lower() in CONFLICT_TYPES
    )
    contradiction_density = min(1.0, conflict_edges / float(total_rel))

    scores = sorted((float(c.score) for c in contradictions), reverse=True)
    n_con = len(contradictions)
    cross = 0
    for c in contradictions:
        aa, ab = int(c.coord_a.area_id), int(c.coord_b.area_id)
        if aa >= 0 and ab >= 0 and aa != ab:
            cross += 1
    cross_rate = cross / float(max(n_con, 1)) if n_con else 0.0

    cls_cnt: dict[str, int] = {k: 0 for k in TRIZ_CLASS_KEYS}
    for c in contradictions:
        k = (c.triz_class or "").strip().lower().replace(" ", "_")
        if k not in cls_cnt:
            k = "parameter_change"
        cls_cnt[k] = cls_cnt.get(k, 0) + 1
    ssum = sum(cls_cnt.values())
    if ssum == 0:
        triz_dist = {k: 0.0 for k in TRIZ_CLASS_KEYS}
    else:
        triz_dist = {k: cls_cnt[k] / float(ssum) for k in TRIZ_CLASS_KEYS}

    hot: dict[tuple[int, int, int | None], float] = defaultdict(float)

    def _add_hot(coord: Any, sc: float) -> None:
        aid, fid = int(coord.area_id), int(coord.family_id)
        hx = coord.hex_id
        if aid < 0 or aid > 11:
            return
        key = (aid, fid if fid >= 0 else -1, int(hx) if hx is not None and hx >= 0 else None)
        hot[key] += sc * 0.5

    for c in contradictions:
        sc = float(c.score)
        _add_hot(c.coord_a, sc)
        _add_hot(c.coord_b, sc)
    hotspots = [
        {
            "area_id": a,
            "family_id": f,
            "hex_id": h,
            "hotspot_score": _r6(v),
        }
        for (a, f, h), v in sorted(hot.items(), key=lambda x: (-x[1], x[0][0], x[0][1], x[0][2] or -1))
    ]

    act_map = {a.concept_id: float(a.activation) for a in activations}
    n_c = max(len(activations), 1)
    activation_energy = sum(act_map.values())

    ic_count = len(innovation_clusters)
    if innovation_clusters:
        inv_scores = [float(cl.innovation_score) for cl in innovation_clusters]
        inv_max = max(inv_scores)
        inv_mean = sum(inv_scores) / float(len(inv_scores))
    else:
        inv_max, inv_mean = 0.0, 0.0

    clusters_detail: list[dict[str, Any]] = []
    for cl in sorted(innovation_clusters, key=lambda x: (-x.innovation_score, x.cluster_id)):
        areas = set()
        for cid in cl.concepts:
            coord = next((a.coordinate for a in activations if a.concept_id == cid), None)
            if coord and 0 <= int(coord.area_id) <= 11:
                areas.add(int(coord.area_id))
        size = max(len(cl.concepts), 1)
        rarity_score = min(1.0, (n_c - size + 1) / float(n_c))
        clusters_detail.append(
            {
                "cluster_id": cl.cluster_id,
                "cluster_rarity_score": _r6(rarity_score),
                "cluster_reach": len(areas),
                "innovation_score": _r6(float(cl.innovation_score)),
                "concept_count": size,
            }
        )

    innovation_pressure = contradiction_density * activation_energy
    semantic_pressure = innovation_pressure

    fam_acc: dict[int, float] = defaultdict(float)
    hex_acc: dict[int, float] = defaultdict(float)
    for a in activations:
        f = int(a.coordinate.family_id)
        if f >= 0:
            fam_acc[f] += float(a.activation)
        h = a.coordinate.hex_id
        if h is not None and int(h) >= 0:
            hex_acc[int(h)] += float(a.activation)

    area_act = {str(i): _r6(area_activation_base.get(i, 0.0)) for i in range(12)}

    pair_cross: dict[tuple[int, int], int] = defaultdict(int)
    for r in relations:
        sa, ta = r.source, r.target
        if sa == ta:
            continue
        ca = next((_concept_area(x) for x in activations if x.concept_id == sa), -1)
        cb = next((_concept_area(x) for x in activations if x.concept_id == ta), -1)
        if ca < 0 or cb < 0 or ca == cb:
            continue
        p = (min(ca, cb), max(ca, cb))
        pair_cross[p] += 1
    domain_coupling: dict[str, float] = {}
    for (a, b), cnt in sorted(pair_cross.items()):
        domain_coupling[f"{a}_{b}"] = min(1.0, cnt / float(total_rel))
    domain_coupling["aggregate_cross_area_edge_rate"] = _r6(
        sum(pair_cross.values()) / float(total_rel)
    )

    deg = [len(topology_adjacency.get(i, [])) for i in range(12)]
    mean_deg = sum(deg) / max(len(deg), 1)
    propagation_resistance = damping * mean_deg

    best_mass = 0.0
    for cl in innovation_clusters:
        m = sum(act_map.get(cid, 0.0) for cid in cl.concepts)
        best_mass = max(best_mass, m)
    concept_mass = best_mass if best_mass > 0 else max(act_map.values()) if act_map else 0.0

    spillover_ratios: list[float] = []
    if len(propagation_history) >= 2:
        h0, h1 = propagation_history[0], propagation_history[1]
        for aid in range(12):
            b = h0.get(aid, 0.0)
            if b < 1e-9:
                continue
            nbs = topology_adjacency.get(aid, [])
            if not nbs:
                continue
            nb_mean = sum(h1.get(nb, 0.0) for nb in nbs) / float(len(nbs))
            spillover_ratios.append(nb_mean / b)
    spillover = sum(spillover_ratios) / float(len(spillover_ratios)) if spillover_ratios else 0.0

    stable_steps = 0
    for t in range(1, len(propagation_history)):
        s0 = sum(propagation_history[t - 1].values())
        s1 = sum(propagation_history[t].values())
        if s1 + 1e-6 >= s0:
            stable_steps += 1
    narr_stab = stable_steps / float(max(len(propagation_history) - 1, 1))

    n_act_final = len([i for i in range(12) if final_propagated.get(i, 0.0) > 0.01])
    vel = n_act_final / float(max(propagation_steps, 1))

    narr_pen = 0.0
    if narratives:
        narr_pen = float(narratives[0].penetration)
    else:
        fams = len({int(a.coordinate.family_id) for a in activations if int(a.coordinate.family_id) >= 0})
        narr_pen = min(1.0, fams / float(max(family_count, 1)))

    route_len = _narrative_route_length(topology_adjacency, propagation_history[0], final_propagated)

    return TRIZDirectMetrics(
        contradiction_count=n_con,
        contradiction_density=_r6(contradiction_density),
        contradiction_scores=scores,
        cross_area_contradiction_rate=_r6(cross_rate),
        triz_class_distribution=triz_dist,
        contradiction_hotspots=hotspots,
        innovation_score=_r6(inv_max),
        innovation_score_mean=_r6(inv_mean),
        innovation_cluster_count=ic_count,
        innovation_clusters_detail=clusters_detail,
        innovation_pressure=_r6(innovation_pressure),
        narrative_penetration=_r6(narr_pen),
        propagation_velocity=_r6(vel),
        spillover_strength=_r6(spillover),
        narrative_stability=_r6(narr_stab),
        narrative_route_length=route_len,
        area_activation={str(k): _r6(v) for k, v in sorted(area_act.items(), key=lambda x: int(x[0]))},
        family_activation={str(k): _r6(v) for k, v in sorted(fam_acc.items())},
        hex_activation={str(k): _r6(v) for k, v in sorted(hex_acc.items())},
        domain_coupling=domain_coupling,
        semantic_pressure=_r6(semantic_pressure),
        activation_energy=_r6(activation_energy),
        propagation_resistance=_r6(propagation_resistance),
        concept_mass=_r6(concept_mass),
    )


def compare_triz_direct(
    previous: TRIZDirectMetrics,
    current: TRIZDirectMetrics,
) -> dict[str, Any]:
    """Corpus A vs B — deltas and cluster emergence (deterministic)."""
    prev_c = max(previous.innovation_cluster_count, 1)
    new_c = max(0, current.innovation_cluster_count - previous.innovation_cluster_count)
    return {
        "contradiction_delta": _r6(current.contradiction_density - previous.contradiction_density),
        "innovation_delta": _r6(current.innovation_score - previous.innovation_score),
        "narrative_shift": _r6(current.narrative_penetration - previous.narrative_penetration),
        "cluster_emergence_rate": _r6(new_c / float(prev_c)),
    }
