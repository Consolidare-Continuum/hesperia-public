# HESPERIA — RAD. TRIZ activation from session topology (co-contradiction surface).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""
Tasks 1–9: concept co-activation from segment concepts, family matrix, contradiction chain,
classification, metrics, hotspots, cluster enrichment, dynamics, cross-plane audit.

Deterministic; no ML. Intended for ``hesperia.tfp`` / session topology output shape.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

# --- Parsing -----------------------------------------------------------------

_AREA_FAM = 10  # public operational areas for coverage denominator


def concept_id_to_area_family(concept_id: str) -> tuple[str, str] | None:
    """
    ``B_A1_F8_004`` → (``A1``, ``A1_F8``).
    Fallback: split on ``_`` and require at least 4 parts starting with B.
    """
    parts = str(concept_id).split("_")
    if len(parts) < 4 or parts[0] != "B":
        return None
    area = parts[1]
    fam_token = parts[2]
    if not area.startswith("A") or not fam_token.startswith("F"):
        return None
    return area, f"{area}_{fam_token}"


def _same_area(fk_a: str, fk_b: str) -> bool:
    return fk_a.split("_", 1)[0] == fk_b.split("_", 1)[0]


def _cross_area(fk_a: str, fk_b: str) -> bool:
    return not _same_area(fk_a, fk_b)


# --- Task 2: hard-coded family matrix ----------------------------------------

# Canonical conflict pairs (unordered), value 1.0
PREDEFINED_FAMILY_CONFLICTS: set[frozenset[str]] = {
    frozenset({"A1_F8", "A2_F20"}),
    frozenset({"A2_F10", "A7_F5"}),
    frozenset({"A3_F12", "A6_F18"}),
    frozenset({"A4_F6", "A9_F14"}),
    frozenset({"A1_F8", "A5_F12"}),
}


def family_conflict_score(fam_a: str, fam_b: str) -> float:
    if fam_a == fam_b:
        return 0.0
    if _same_area(fam_a, fam_b):
        base = 0.2
    else:
        base = 0.5
    key = frozenset({fam_a, fam_b})
    if key in PREDEFINED_FAMILY_CONFLICTS:
        return 1.0
    return base


def build_family_contradiction_matrix(family_keys: list[str]) -> dict[str, dict[str, float]]:
    """Symmetric matrix as nested dicts (Task 2)."""
    keys = sorted(set(family_keys))
    out: dict[str, dict[str, float]] = {}
    for a in keys:
        row: dict[str, float] = {}
        for b in keys:
            row[b] = round(family_conflict_score(a, b), 4)
        out[a] = row
    return out


# --- Task 1: co-activation graph ---------------------------------------------

def build_concept_coactivation_graph(
    session_topology: dict[str, Any],
    *,
    min_concept_score: float = 1e-6,
    max_pairs_per_segment: int = 400,
) -> list[dict[str, Any]]:
    """
    Per segment: concepts with score > threshold → unordered pairs, count co-occurrences.
    Aggregate counts; normalize weights to [0,1] by max count.
    """
    segments = session_topology.get("segments") or []
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for seg in segments:
        concepts = seg.get("concepts") or {}
        active = sorted(
            [c for c, s in concepts.items() if float(s or 0) > min_concept_score],
            key=str,
        )
        pairs = list(itertools.combinations(active, 2))
        if len(pairs) > max_pairs_per_segment:
            pairs = pairs[:max_pairs_per_segment]
        for a, b in pairs:
            key = tuple(sorted((a, b)))
            pair_counts[key] += 1
    if not pair_counts:
        return []
    mx = max(pair_counts.values())
    mx = max(mx, 1)
    edges: list[dict[str, Any]] = []
    for (ci, cj), cnt in sorted(pair_counts.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
        w = round(cnt / mx, 6)
        edges.append(
            {
                "concept_i": ci,
                "concept_j": cj,
                "coactivation_weight": w,
                "cooccurrence_count": int(cnt),
            }
        )
    return edges


# --- Tasks 3–4 ---------------------------------------------------------------

def build_concept_contradictions_raw(
    coactivation_edges: list[dict[str, Any]],
    family_matrix: dict[str, dict[str, float]] | None = None,
    *,
    sparse_family_pair_weights: dict[tuple[str, str], float] | None = None,
) -> list[dict[str, Any]]:
    """
    If ``sparse_family_pair_weights`` is set (v0.5.2), only pairs with a sparse family edge
    contribute; ``family_conflict`` comes from the sparse weight (non-uniform, locality-shaped).
    """
    raw: list[dict[str, Any]] = []
    for e in coactivation_edges:
        ci, cj = e["concept_i"], e["concept_j"]
        w = float(e["coactivation_weight"])
        pa = concept_id_to_area_family(ci)
        pb = concept_id_to_area_family(cj)
        if not pa or not pb:
            if sparse_family_pair_weights is not None:
                continue
            fc = 0.5
        elif sparse_family_pair_weights is not None:
            key = tuple(sorted((pa[1], pb[1])))
            fc = float(sparse_family_pair_weights.get(key) or 0.0)
            if fc < 1e-9:
                # Cross-area: no edge in sparse graph → drop (cluster / locality gate).
                if not _same_area(pa[1], pb[1]):
                    continue
                # Same-area: weak fallback from dense matrix (never 0.2/0.5 literals — use scaled prior).
                d = float(
                    (family_matrix or {}).get(pa[1], {}).get(
                        pb[1], family_conflict_score(pa[1], pb[1])
                    )
                )
                # Map flat 0.2 dense prior into weak-link band (never emit 0.2/0.5).
                fc = max(0.26, min(0.34, 0.45 * d + 0.17))
            if fc < 0.25:
                continue
        else:
            fc = family_conflict_score(pa[1], pb[1]) if family_matrix is None else float(
                family_matrix.get(pa[1], {}).get(pb[1], family_conflict_score(pa[1], pb[1]))
            )
        score = round(w * fc, 6)
        raw.append(
            {
                "pair": [ci, cj],
                "coactivation": w,
                "family_conflict": fc,
                "raw_contradiction_score": score,
            }
        )
    return raw


def classify_triz_class(family_conflict: float, same_area: bool, cross_area: bool) -> str:
    # Align with v0.5.2 sparse cap (0.9): treat near-max weights as strong contradiction.
    if family_conflict >= 0.88 - 1e-9:
        return "counterbalance"
    if same_area:
        return "parameter_change"
    if cross_area:
        return "dynamic_adaptation"
    return "segmentation"


def build_concept_contradictions_classified(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in raw_rows:
        ci, cj = r["pair"][0], r["pair"][1]
        pa = concept_id_to_area_family(ci)
        pb = concept_id_to_area_family(cj)
        sa = bool(pa and pb and _same_area(pa[1], pb[1]))
        ca = bool(pa and pb and _cross_area(pa[1], pb[1]))
        fc = float(r["family_conflict"])
        cls = classify_triz_class(fc, sa, ca)
        out.append(
            {
                "pair": [ci, cj],
                "coactivation": r["coactivation"],
                "family_conflict": fc,
                "raw_contradiction_score": r["raw_contradiction_score"],
                "triz_class": cls,
            }
        )
    return out


# --- Task 5 ------------------------------------------------------------------

def compute_triz_metrics_v1(
    classified: list[dict[str, Any]],
    *,
    universe_concepts: set[str],
) -> dict[str, Any]:
    n = len(classified)
    u = len(universe_concepts)
    total_pairs = u * (u - 1) / 2 if u >= 2 else 0.0
    density = (n / total_pairs) if total_pairs > 0 else 0.0
    cross_n = 0
    for r in classified:
        a, b = r["pair"][0], r["pair"][1]
        pa, pb = concept_id_to_area_family(a), concept_id_to_area_family(b)
        if pa and pb and _cross_area(pa[1], pb[1]):
            cross_n += 1
    cross_rate = cross_n / n if n else 0.0
    mean_score = sum(float(r["raw_contradiction_score"]) for r in classified) / n if n else 0.0
    return {
        "contradiction_count": n,
        "contradiction_density": round(density, 8),
        "cross_area_contradiction_rate": round(cross_rate, 6),
        "mean_contradiction_score": round(mean_score, 6),
        "universe_concept_count": u,
    }


# --- Task 6 ------------------------------------------------------------------

def build_contradiction_hotspots(
    classified: list[dict[str, Any]],
    top_n: int = 10,
) -> list[dict[str, Any]]:
    fam_sum: dict[str, float] = defaultdict(float)
    fam_pairs: dict[str, int] = defaultdict(int)
    for r in classified:
        s = float(r["raw_contradiction_score"])
        for cid in r["pair"]:
            parsed = concept_id_to_area_family(cid)
            if not parsed:
                continue
            fk = parsed[1]
            fam_sum[fk] += s
            fam_pairs[fk] += 1
    ranked = sorted(fam_sum.items(), key=lambda x: (-x[1], x[0]))[:top_n]
    return [
        {
            "family": fk,
            "contradiction_score": round(score, 6),
            "connected_pairs": int(fam_pairs[fk]),
        }
        for fk, score in ranked
    ]


# --- Task 7 ------------------------------------------------------------------

def enrich_innovation_clusters(
    innovation_clusters: list[dict[str, Any]] | None,
    pair_scores: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    """Mean raw contradiction over cluster concept pairs; density = covered pairs / possible pairs (Task 7)."""
    clusters = innovation_clusters or []
    out: list[dict[str, Any]] = []
    for cl in clusters:
        concepts = [str(x) for x in (cl.get("concepts") or [])]
        n_c = len(concepts)
        pair_vals: list[float] = []
        for a, b in itertools.combinations(sorted(concepts), 2):
            key = tuple(sorted((a, b)))
            if key in pair_scores:
                pair_vals.append(pair_scores[key])
        mean_contra = sum(pair_vals) / len(pair_vals) if pair_vals else 0.0
        max_pairs = n_c * (n_c - 1) / 2 if n_c >= 2 else 0.0
        density = (len(pair_vals) / max_pairs) if max_pairs > 0 else 0.0
        row = dict(cl)
        row["innovation_score"] = round(mean_contra, 6)
        row["contradiction_density"] = round(density, 6)
        out.append(row)
    return out


# --- Task 8 ------------------------------------------------------------------

def compute_triz_dynamics(
    metrics: dict[str, Any],
    coactivation_edges: list[dict[str, Any]],
    state_sequence: list[str],
) -> dict[str, Any]:
    n_edges = len(coactivation_edges)
    n_nodes = len(
        {e["concept_i"] for e in coactivation_edges} | {e["concept_j"] for e in coactivation_edges}
    )
    avg_degree = (2 * n_edges / n_nodes) if n_nodes else 0.0
    mean_score = float(metrics.get("mean_contradiction_score") or 0.0)
    cross_rate = float(metrics.get("cross_area_contradiction_rate") or 0.0)
    density = float(metrics.get("contradiction_density") or 0.0)
    areas = {a for a in state_sequence if a}
    area_coverage = len(areas) / float(_AREA_FAM) if _AREA_FAM else 0.0
    prop_vel = round(mean_score * (avg_degree / max(n_nodes, 1)), 8)
    spill = round(cross_rate, 8)
    narr = round(density * area_coverage, 8)
    return {
        "propagation_velocity": prop_vel,
        "spillover_strength": spill,
        "narrative_penetration": narr,
        "avg_graph_degree": round(avg_degree, 6),
        "area_coverage": round(area_coverage, 6),
    }


# --- Task 9 ------------------------------------------------------------------

def topology_mean_max_activation(session_topology: dict[str, Any]) -> float:
    segs = session_topology.get("segments") or []
    if not segs:
        return 0.0
    vals: list[float] = []
    for seg in segs:
        concepts = seg.get("concepts") or {}
        if not concepts:
            vals.append(0.0)
        else:
            vals.append(max(float(v) for v in concepts.values()))
    return sum(vals) / len(vals)


def build_cross_plane_audit(
    session_topology: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    topo_act = topology_mean_max_activation(session_topology)
    n_contra = int(metrics.get("contradiction_count") or 0)
    anomalies: list[dict[str, Any]] = []
    if topo_act > 0.5 and n_contra == 0:
        anomalies.append(
            {
                "code": "TRIZ_DEAD_LAYER",
                "severity": "critical",
                "detail": "topology_activation>0.5 but contradiction_count==0",
                "topology_activation": round(topo_act, 6),
                "contradiction_count": n_contra,
            }
        )
    return {
        "topology_activation": round(topo_act, 6),
        "contradiction_count": n_contra,
        "anomalies": anomalies,
        "pass": len(anomalies) == 0,
    }


def triz_activation_bundle_filename(session_id: str, bundle_json_name: str) -> str:
    """
    Single-folder bundle layout: ``12_<session_slug>_<artifact>.json`` (no ``triz_activation/`` subdirs).
    Matches numbered TFP artifacts (``10_``, ``11_``, …).
    """
    s = str(session_id or "").strip() or "session"
    slug = "".join(c if c.isalnum() or c in "-._" else "_" for c in s)
    return f"12_{slug}_{bundle_json_name}"


# --- Orchestrator ------------------------------------------------------------

def collect_family_keys_from_edges(coactivation_edges: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for e in coactivation_edges:
        for cid in (e["concept_i"], e["concept_j"]):
            p = concept_id_to_area_family(cid)
            if p:
                keys.add(p[1])
    return sorted(keys)


def collect_universe_concepts(coactivation_edges: list[dict[str, Any]]) -> set[str]:
    s: set[str] = set()
    for e in coactivation_edges:
        s.add(e["concept_i"])
        s.add(e["concept_j"])
    return s


def synthetic_clusters_from_coactivation_edges(
    coactivation_edges: list[dict[str, Any]],
    *,
    max_pairs: int = 400,
    max_clusters: int = 60,
    max_families_per_cluster: int = 36,
) -> list[dict[str, Any]]:
    """When TRIZ innovation_clusters are absent, build coarse family components from strong coactivation."""
    fam_w: dict[tuple[str, str], float] = defaultdict(float)
    for e in coactivation_edges:
        pa = concept_id_to_area_family(e["concept_i"])
        pb = concept_id_to_area_family(e["concept_j"])
        if not pa or not pb:
            continue
        a, b = pa[1], pb[1]
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        fam_w[key] += float(e.get("cooccurrence_count") or 0) + float(e.get("coactivation_weight") or 0)

    ranked = sorted(fam_w.items(), key=lambda x: -x[1])[:max_pairs]
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for (a, b), _ in ranked:
        union(a, b)

    comps: dict[str, list[str]] = defaultdict(list)
    for f in parent:
        comps[find(f)].append(f)
    out: list[dict[str, Any]] = []
    for i, members in enumerate(sorted(comps.values(), key=lambda m: -len(m))):
        if len(members) < 2:
            continue
        out.append(
            {
                "cluster_id": f"synth_cc_{i}",
                "families": sorted(members)[:max_families_per_cluster],
            }
        )
        if len(out) >= max_clusters:
            break
    return out


def run_topology_triz_activation(
    session_topology: dict[str, Any],
    *,
    triz_complete: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run tasks 1–9. Returns dict with keys matching artifact filenames (no paths).
    Contradictions use **v0.5.2 sparse family weights** when built successfully.
    """
    graph = build_concept_coactivation_graph(session_topology)
    fam_keys = collect_family_keys_from_edges(graph)
    family_matrix = build_family_contradiction_matrix(fam_keys)

    cc_list: list[dict[str, Any]] = []
    clusters_src = None
    if triz_complete:
        tc = triz_complete.get("triz_complete") or triz_complete
        clusters_src = tc.get("innovation_clusters")
        for cl in clusters_src or []:
            if isinstance(cl, dict):
                cc_list.append(
                    {
                        "cluster_id": str(cl.get("cluster_id", "")),
                        "concepts": list(cl.get("concepts") or []),
                    }
                )
    if not cc_list:
        cc_list = synthetic_clusters_from_coactivation_edges(graph)

    from hesperia.extensions.triz.family_weights_sparsify import build_sparse_family_weights

    sparse_body = build_sparse_family_weights(family_matrix, cc_list)
    sparse_lookup = {
        tuple(sorted((str(e["family_i"]), str(e["family_j"])))): float(e["weight"])
        for e in sparse_body.get("edges") or []
    }
    raw = build_concept_contradictions_raw(
        graph,
        family_matrix,
        sparse_family_pair_weights=sparse_lookup,
    )
    classified = build_concept_contradictions_classified(raw)
    universe = collect_universe_concepts(graph)
    metrics = compute_triz_metrics_v1(classified, universe_concepts=universe)
    hotspots = build_contradiction_hotspots(classified, top_n=10)
    pair_scores = {
        tuple(sorted((r["pair"][0], r["pair"][1]))): float(r["raw_contradiction_score"])
        for r in raw
    }
    enriched = enrich_innovation_clusters(clusters_src, pair_scores)
    state_sequence = session_topology.get("state_sequence") or []
    dynamics = compute_triz_dynamics(metrics, graph, state_sequence)
    audit = build_cross_plane_audit(session_topology, metrics)

    sparse_for_disk = {k: v for k, v in sparse_body.items() if k != "matrix_sparse"}
    sparse_for_disk["matrix_sparse_omitted"] = True

    return {
        "concept_coactivation_graph.json": {"edges": graph, "edge_count": len(graph)},
        "family_contradiction_matrix.json": family_matrix,
        "concept_clusters.json": {"clusters": cc_list},
        "family_weights_sparse_v052.json": sparse_for_disk,
        "concept_contradictions_raw.json": {"contradictions": raw},
        "concept_contradictions_classified.json": {"contradictions": classified},
        "triz_metrics_v1.json": metrics,
        "contradiction_hotspots.json": {"hotspots": hotspots},
        "innovation_clusters_enriched.json": {"clusters": enriched},
        "triz_dynamics.json": dynamics,
        "cross_plane_audit.json": audit,
    }


def triz_activation_pipeline_fail(audit: dict[str, Any]) -> bool:
    """True if critical cross-plane anomaly (Task 9 / Task 10 gate)."""
    for a in audit.get("anomalies") or []:
        if str(a.get("severity")) == "critical":
            return True
    return False
