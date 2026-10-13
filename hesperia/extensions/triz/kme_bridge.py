# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
KME pipeline integration: single ActiveGraph + topology from activation trace / coordinates.
Read-only; no second graph type.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from hesperia.extensions.triz.models import (
    ContradictionSignal,
    InnovationCluster,
    MatrixCoordinate,
    NarrativeSignal,
    TRIZSignals,
)

if TYPE_CHECKING:
    from core.domain.models import ActiveGraph


def _parse_area(s: str) -> int | None:
    t = (s or "").strip()
    if t.isdigit():
        v = int(t)
        return v if 0 <= v <= 11 else None
    m = re.match(r"^A(\d+)$", t, re.I)
    if m:
        v = int(m.group(1)) - 1
        return v if 0 <= v <= 11 else None
    return None


def _parse_family(fam: str, area_s: str) -> int | None:
    t = (fam or "").strip()
    if t.isdigit():
        v = int(t)
        return v if 0 <= v < 288 else None
    if "_" in t:
        parts = t.split("_", 1)
        if parts[-1].isdigit():
            v = int(parts[-1])
            return v if 0 <= v < 288 else None
    return None


def build_topology_from_activation_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    """Trace rows from explainability.build_activation_trace → concept_to_area / concept_to_family."""
    c2a: dict[str, int] = {}
    c2f: dict[str, int] = {}
    for row in trace:
        cid = str(row.get("concept_id") or "")
        if not cid:
            continue
        aid = _parse_area(str(row.get("area_id") or ""))
        fid = _parse_family(str(row.get("family_id") or ""), str(row.get("area_id") or ""))
        if aid is not None:
            c2a[cid] = aid
        if fid is not None:
            c2f[cid] = fid
    topo: dict[str, Any] = {}
    if c2a:
        topo["concept_to_area"] = dict(sorted(c2a.items()))
    if c2f:
        topo["concept_to_family"] = dict(sorted(c2f.items()))
    return topo


def topology_from_graph_coordinates(graph: "ActiveGraph") -> dict[str, Any] | None:
    if not graph.concept_coordinates:
        return None
    c2a: dict[str, int] = {}
    c2f: dict[str, int] = {}
    for cid, coord in sorted(graph.concept_coordinates.items()):
        if "area_id" in coord:
            a = int(coord["area_id"])
            if 0 <= a <= 11 and a not in (5, 11) or True:
                c2a[cid] = a
        if "family_id" in coord:
            c2f[cid] = int(coord["family_id"])
    topo: dict[str, Any] = {}
    if c2a:
        topo["concept_to_area"] = c2a
    if c2f:
        topo["concept_to_family"] = c2f
    return topo or None


def _row_to_contradiction_signal(row: dict[str, Any]) -> ContradictionSignal:
    aa = row.get("area_a")
    ab = row.get("area_b")
    fa = row.get("family_a")
    fb = row.get("family_b")
    ha = row.get("hex_a")
    hb = row.get("hex_b")

    def _i(x: Any, default: int = -1) -> int:
        if x is None:
            return default
        try:
            return int(x)
        except (TypeError, ValueError):
            return default

    def _hi(x: Any) -> int | None:
        if x is None:
            return None
        try:
            return int(x)
        except (TypeError, ValueError):
            return None

    return ContradictionSignal(
        concept_a=str(row["concept_a"]),
        concept_b=str(row["concept_b"]),
        score=float(row["score"]),
        triz_class=str(row.get("triz_class") or ""),
        coord_a=MatrixCoordinate(_i(aa), _i(fa), _hi(ha)),
        coord_b=MatrixCoordinate(_i(ab), _i(fb), _hi(hb)),
    )


def _clusters_from_dict(rows: list[dict[str, Any]]) -> list[InnovationCluster]:
    out: list[InnovationCluster] = []
    for cl in rows:
        out.append(
            InnovationCluster(
                cluster_id=str(cl["cluster_id"]),
                concepts=list(cl["concepts"]),
                rarity=float(cl["rarity"]),
                contradiction_density=float(cl["contradiction_density"]),
                propagation_reach=float(cl["propagation_reach"]),
                innovation_score=float(cl["innovation_score"]),
            )
        )
    return out


def _narratives_from_dict(rows: list[dict[str, Any]]) -> list[NarrativeSignal]:
    return [
        NarrativeSignal(
            narrative_id=str(n["narrative_id"]),
            activated_areas=list(n["activated_areas"]),
            penetration=float(n["penetration"]),
            velocity=float(n["velocity"]),
            stability=float(n["stability"]),
        )
        for n in rows
    ]


def _attach_direct_metrics(
    active_graph: "ActiveGraph",
    topology: dict[str, Any] | None,
    sig: TRIZSignals,
    *,
    narrative_id: str,
    propagation_steps: int = 3,
    damping: float = 0.2,
) -> None:
    from hesperia.extensions.triz.direct_outputs import build_triz_direct_metrics
    from hesperia.extensions.triz.pipeline import build_triz_activations_and_relations
    from hesperia.extensions.triz.propagation_engine import aggregate_area_activation, propagate_activation_with_history
    from hesperia.extensions.triz.topology_metrics import canonical_area_adjacency, neighbors_from_adjacency

    acts, rels = build_triz_activations_and_relations(active_graph, topology)
    neighbors = neighbors_from_adjacency(canonical_area_adjacency())
    fc = int((topology or {}).get("total_families") or 240)
    area_act = aggregate_area_activation(acts)
    if not area_act:
        area_act = {a: 0.0 for a in range(12)}
    hist, final = propagate_activation_with_history(
        area_act, neighbors, steps=propagation_steps, damping=damping
    )
    sig.direct_metrics = build_triz_direct_metrics(
        acts,
        rels,
        neighbors,
        sig.contradictions,
        sig.innovation_clusters,
        sig.narratives,
        propagation_history=hist,
        final_propagated=final,
        propagation_steps=propagation_steps,
        damping=damping,
        family_count=fc,
        area_activation_base=dict(area_act),
    )


def run_triz_for_kme(
    active_graph: "ActiveGraph",
    topology: dict[str, Any] | None,
    *,
    narrative_id: str = "narrative_primary",
) -> TRIZSignals:
    """Run TRIZ on the same ActiveGraph instance; return TRIZSignals for MetricReport."""
    from hesperia.extensions.triz.guards import TrizStructuralViolation
    from hesperia.extensions.triz.pipeline import run_triz_analysis_complete, run_triz_layer

    use_full = bool(
        topology
        and topology.get("concept_to_area")
        and topology.get("concept_to_family")
    )
    if use_full:
        try:
            full = run_triz_analysis_complete(
                active_graph,
                topology,
                narrative_id=narrative_id,
                topology_mode=True,
            )
            routes = list(full.get("topology", {}).get("narrative_routes") or [])
            sig = TRIZSignals(
                contradictions=[_row_to_contradiction_signal(r) for r in full.get("contradictions") or []],
                innovation_clusters=_clusters_from_dict(list(full.get("innovation_clusters") or [])),
                narratives=_narratives_from_dict(list(full.get("narratives") or [])),
                narrative_routes=routes,
            )
            _attach_direct_metrics(active_graph, topology, sig, narrative_id=narrative_id)
            return sig
        except TrizStructuralViolation:
            pass

    return run_triz_layer(active_graph, topology, narrative_id=narrative_id)
