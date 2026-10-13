# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""TRIZ end-to-end pipeline: activations + relations → TRIZSignals."""

from __future__ import annotations

from typing import Any

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.models import ConceptActivation, ConceptRelation, MatrixCoordinate, TRIZSignals
from hesperia.extensions.triz.topology_metrics import canonical_area_adjacency, neighbors_from_adjacency
from hesperia.extensions.triz.triz_pipeline import run_triz_analysis


def active_graph_from_payload(payload: dict[str, Any]) -> ActiveGraph:
    """Build ActiveGraph from API/KME-style JSON."""
    nodes: dict[str, ActiveNode] = {}
    raw_nodes = payload.get("nodes") or {}
    for cid in sorted(raw_nodes.keys()):
        v = raw_nodes[cid]
        if isinstance(v, dict):
            hc = v.get("hitCount", v.get("hit_count", 0))
        else:
            hc = int(v) if v is not None else 0
        nodes[cid] = ActiveNode(concept_id=cid, hit_count=max(0, int(hc)))
    edges: list[ActiveEdge] = []
    for e in payload.get("edges") or []:
        s = e.get("source") or e.get("source_concept_id") or ""
        t = e.get("target") or e.get("target_concept_id") or ""
        typ = e.get("type") or e.get("relation_type") or ""
        if s and t:
            edges.append(
                ActiveEdge(
                    source_concept_id=str(s),
                    target_concept_id=str(t),
                    relation_type=str(typ),
                )
            )
    edges.sort(key=lambda x: (x.source_concept_id, x.target_concept_id, x.relation_type))
    return ActiveGraph(nodes=nodes, edges=edges)


def _parse_int_map(topology: dict[str, Any] | None, key: str) -> dict[str, int] | None:
    if not topology or key not in topology:
        return None
    m = topology.get(key) or {}
    return {str(k): int(v) for k, v in sorted(m.items(), key=lambda x: str(x[0]))}


def build_triz_activations_and_relations(
    active_graph: ActiveGraph,
    topology: dict[str, Any] | None,
) -> tuple[list[ConceptActivation], list[ConceptRelation]]:
    mx = max((n.hit_count for n in active_graph.nodes.values()), default=1)
    mx = max(mx, 1)
    c2a = _parse_int_map(topology, "concept_to_area") or {}
    c2f = _parse_int_map(topology, "concept_to_family") or {}
    acts: list[ConceptActivation] = []
    for cid, n in sorted(active_graph.nodes.items()):
        act = min(1.0, float(n.hit_count) / float(mx))
        ai = int(c2a[cid]) if cid in c2a else -1
        fi = int(c2f[cid]) if cid in c2f else -1
        acts.append(ConceptActivation(cid, act, MatrixCoordinate(ai, fi, None)))
    rels = [
        ConceptRelation(e.source_concept_id, e.target_concept_id, e.relation_type or "", 1.0)
        for e in active_graph.edges
    ]
    rels.sort(key=lambda r: (r.source, r.target, r.relation_type))
    return acts, rels


def run_triz_layer(
    active_graph: ActiveGraph,
    topology: dict[str, Any] | None = None,
    *,
    narrative_id: str = "narrative_primary",
) -> TRIZSignals:
    """Single path: graph → ConceptActivation / ConceptRelation → run_triz_analysis."""
    acts, rels = build_triz_activations_and_relations(active_graph, topology)
    neighbors = neighbors_from_adjacency(canonical_area_adjacency())
    fc = int((topology or {}).get("total_families") or 240)
    return run_triz_analysis(
        acts,
        rels,
        neighbors,
        narrative_id=narrative_id,
        family_count=fc,
    )


def triz_report_to_dict(report: TRIZSignals) -> dict[str, Any]:
    """Deterministic JSON-shaped dict."""
    return report.to_dict()


def _build_concept_mapping(topology: dict[str, Any] | None) -> dict[str, Any]:
    if not topology:
        return {}
    cm = topology.get("concept_matrix")
    if isinstance(cm, dict) and cm:
        return {str(k): dict(v) if isinstance(v, dict) else v for k, v in sorted(cm.items(), key=lambda x: str(x[0]))}
    c2a = _parse_int_map(topology, "concept_to_area") or {}
    c2f = _parse_int_map(topology, "concept_to_family") or {}
    c2h: dict[str, int] = {}
    hx = topology.get("concept_to_hex")
    if isinstance(hx, dict):
        for k, v in sorted(hx.items(), key=lambda x: str(x[0])):
            try:
                c2h[str(k)] = int(v)
            except (TypeError, ValueError):
                pass
    out: dict[str, Any] = {}
    for cid in sorted(set(c2a) | set(c2f) | set(c2h)):
        out[cid] = {
            "area_id": int(c2a.get(cid, -1)),
            "family_id": int(c2f.get(cid, -1)),
            "hex_id": c2h.get(cid),
        }
    return out


def run_triz_analysis_complete(
    active_graph: ActiveGraph,
    topology: dict[str, Any] | None = None,
    *,
    narrative_id: str = "narrative_primary",
    run_id: str | None = None,
    topology_mode: bool = True,
) -> dict[str, Any]:
    """
    Series-2 integrated TRIZ: topology binding, hotspots, hex peaks, topology propagation, routes, reports, CSV.
    """
    from collections import defaultdict

    from hesperia.extensions.triz.exporters import triz_topology_csv_bundle
    from hesperia.extensions.triz.family_clustering import get_conflict_hotspots
    from hesperia.extensions.triz.guards import guard_no_meta_lexical_activation
    from hesperia.extensions.triz.hex_signals import aggregate_hex_pressure, detect_hex_pressure_peaks
    from hesperia.extensions.triz.narrative_routes import (
        extract_narrative_routes,
        get_strongest_narrative_paths,
        summarize_routes_for_monitor,
    )
    from hesperia.extensions.triz.propagation_engine import propagate_topology_mode
    from hesperia.extensions.triz.report_builders import build_all_reports
    from hesperia.extensions.triz.time_series import persistent_contradictions, update_signal_history
    from hesperia.extensions.triz.topology_binding import bind_contradiction_to_topology

    c2a = _parse_int_map(topology, "concept_to_area")
    concept_mapping = _build_concept_mapping(topology)
    if topology_mode and c2a:
        guard_no_meta_lexical_activation(c2a)

    report = run_triz_layer(active_graph, topology, narrative_id=narrative_id)
    base = triz_report_to_dict(report)

    prop_topo: dict[str, Any] | None = None
    c2f = _parse_int_map(topology, "concept_to_family")
    if topology_mode and c2a and c2f:
        prop_topo = propagate_topology_mode(
            active_graph,
            c2a,
            c2f,
            report.contradictions,
        )

    con_rows: list[dict[str, Any]] = []
    for c in sorted(report.contradictions, key=lambda x: (-x.score, x.concept_a, x.concept_b)):
        row: dict[str, Any] = {
            "area_cluster": list(c.area_cluster),
            "concept_a": c.concept_a,
            "concept_b": c.concept_b,
            "score": round(float(c.score), 6),
            "triz_class": c.triz_class,
        }
        if concept_mapping:
            b = bind_contradiction_to_topology(c, concept_mapping)
            row["adjacent_areas"] = b["adjacent_areas"]
            row["area_a"] = b["area_a"]
            row["area_b"] = b["area_b"]
            row["family_a"] = b["family_a"]
            row["family_b"] = b["family_b"]
            row["hex_a"] = b["hex_a"]
            row["hex_b"] = b["hex_b"]
            row["locality_score"] = b["locality_score"]
            row["same_area"] = b["same_area"]
        con_rows.append(row)

    family_hotspots = (
        get_conflict_hotspots(report.contradictions, concept_mapping, 20)
        if concept_mapping
        else []
    )

    area_scores: dict[int, list[float]] = defaultdict(list)
    for row in con_rows:
        for ak in ("area_a", "area_b"):
            a = row.get(ak)
            if a is not None and isinstance(a, int) and a >= 0:
                area_scores[a].append(float(row["score"]))
    area_hotspots = [
        {"area": a, "hotspot_score": round(sum(v) / len(v), 6)}
        for a, v in sorted(area_scores.items(), key=lambda x: (-sum(x[1]) / len(x[1]), x[0]))
    ]

    active_hexes = None
    if topology and isinstance(topology.get("active_hexes"), dict):
        active_hexes = {int(k): float(v) for k, v in topology["active_hexes"].items()}
    hex_p: dict[int, float] = {}
    peaks: list[dict[str, Any]] = []
    if concept_mapping:
        hex_p = aggregate_hex_pressure(active_hexes, report.contradictions, concept_mapping)
        peaks = detect_hex_pressure_peaks(hex_p, concept_mapping)

    routes: list[dict[str, Any]] = []
    paths: list[dict[str, Any]] = []
    mon: dict[str, Any] = {
        "blocked_areas": [],
        "dominant_routes": [],
        "spillover_targets": [],
        "strongest_paths": [],
    }
    if prop_topo:
        routes = extract_narrative_routes(prop_topo)
        paths = get_strongest_narrative_paths(narrative_id, prop_topo, top_k=5)
        mon = summarize_routes_for_monitor(prop_topo, narrative_id=narrative_id)

    persistent: list[str] = []
    if run_id:
        update_signal_history(
            run_id,
            {
                "contradictions": con_rows,
                "innovation_clusters": base["innovation_clusters"],
                "narratives": base["narratives"],
            },
        )
        persistent = persistent_contradictions(run_id, min_runs=3)

    ctx: dict[str, Any] = {
        "contradictions": con_rows,
        "family_hotspots": family_hotspots,
        "innovation_clusters": base["innovation_clusters"],
        "narratives": base["narratives"],
        "narrative_monitor": mon,
        "persistent_contradictions": persistent,
        "propagation_topology": prop_topo or {},
    }
    reports = build_all_reports(ctx)

    from hesperia.extensions.triz.commercial_intelligence import commercial_intelligence_to_dict

    out: dict[str, Any] = {
        "atomic_metrics": report.direct_metrics.to_dict() if report.direct_metrics else {},
        "commercial_intelligence": commercial_intelligence_to_dict(report),
        "contradictions": con_rows,
        "csv_exports": triz_topology_csv_bundle(
            con_rows,
            base["innovation_clusters"],
            routes,
            paths,
            area_hotspots,
        ),
        "innovation_clusters": base["innovation_clusters"],
        "narratives": base["narratives"],
        "reports": reports,
        "topology": {
            "area_hotspots": area_hotspots,
            "family_hotspots": family_hotspots,
            "hex_pressure_peaks": peaks,
            "narrative_routes": routes,
            "strongest_paths": paths,
        },
    }
    return out
