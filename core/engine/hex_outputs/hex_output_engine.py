# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Product-grade maps — **Hesperia Engine Dynamics v0.5** (product signal layer).

Public API uses microstructure_* names — apply_public_projection strips keys containing 'hex'.
Sparse scene = top-hit families × nh slots; not full 72k grid (performance + artifact size).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from core.engine.hex_outputs.cluster_gravity import compute_cluster_gravity
from core.engine.hex_outputs.contradiction_front import compute_contradiction_front
from core.engine.hex_outputs.hotspot_map import compute_hotspot_map
from core.engine.hex_outputs.multiscale_consistency import compute_family_multiscale_consistency
from core.engine.hex_outputs.propagation_corridors import compute_propagation_corridors
from core.projection.area_math_grain import active_family_count

__all__ = [
    "HexOutputParams",
    "compute_hex_outputs",
    "serialize_hex_outputs",
    "build_sparse_hex_scene",
    "attach_hex_product_outputs",
    "attach_microstructure_analytics_public",
]


@dataclass(frozen=True)
class HexOutputParams:
    hotspot_lambda: float = 0.45
    propagation_alpha: float = 0.12
    propagation_beta: float = 0.06
    propagation_steps: int = 2
    corridor_top_k: int = 48
    gravity_eps: float = 1e-6
    cross_family_distance: float = 80.0


def compute_hex_outputs(
    hex_activation: np.ndarray | list[float],
    adjacency: list[list[int]],
    contradiction_matrix: np.ndarray | list[list[float]],
    resistance: np.ndarray | list[float],
    family_hex_map: Mapping[int, list[int] | tuple[int, ...]],
    family_activation: Mapping[int, float] | np.ndarray,
    distance_matrix: np.ndarray | list[list[float]],
    *,
    params: HexOutputParams | None = None,
) -> dict[str, Any]:
    """
    Single entry: narrative hotspots, contradiction fronts, propagation corridors,
    cluster gravity, multiscale consistency.
    """
    p = params or HexOutputParams()
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1)
    c = np.asarray(contradiction_matrix, dtype=np.float64)
    r = np.asarray(resistance, dtype=np.float64).reshape(-1)
    d = np.asarray(distance_matrix, dtype=np.float64)

    hot = compute_hotspot_map(a, adjacency, lam=p.hotspot_lambda)
    front = compute_contradiction_front(a, adjacency, c)
    prop = compute_propagation_corridors(
        a,
        adjacency,
        r,
        alpha=p.propagation_alpha,
        beta=p.propagation_beta,
        steps=p.propagation_steps,
        corridor_top_k=p.corridor_top_k,
    )
    grav = compute_cluster_gravity(a, d, eps=p.gravity_eps)
    consist = compute_family_multiscale_consistency(
        a, family_hex_map, family_activation
    )

    return {
        "hex_hotspot_map": hot,
        "hex_contradiction_front": front,
        "propagation_corridors": prop,
        "hex_cluster_gravity": grav,
        "family_multiscale_consistency": consist,
    }


def serialize_hex_outputs(raw: dict[str, Any], *, digits: int = 6) -> dict[str, Any]:
    """JSON-friendly lists (truncate large matrices in callers if needed).

    METRIC-24/25: attach path_metric_cost over corridor hex_graph edges (24_SPEC §5).
    Formula matches ``runtime.services.path_metric.compute_s_path`` for ``hex_graph``
    without importing runtime (core↛runtime boundary).
    """
    prop = raw["propagation_corridors"]
    flow = prop["propagation_flow_matrix"]
    flow_list = np.asarray(flow).round(digits).tolist()
    corridor_edges = [
        {"from": e["from"], "to": e["to"], "gradient": round(float(e["gradient"]), digits)}
        for e in prop["corridor_edges"]
    ]
    path_cost = 0.0
    for edge in corridor_edges:
        path_cost += abs(float(edge["gradient"]))
    path_layers = ["hex_graph"] if corridor_edges else []
    return {
        "hex_hotspot_map": np.asarray(raw["hex_hotspot_map"]).round(digits).tolist(),
        "hex_contradiction_front": np.asarray(raw["hex_contradiction_front"]).round(digits).tolist(),
        "propagation_corridors": {
            "hex_propagation_vector": np.asarray(prop["hex_propagation_vector"]).round(digits).tolist(),
            "propagation_flow_matrix": flow_list,
            "corridor_edges": corridor_edges,
            "path_metric_cost": round(path_cost, digits),
            "path_metric_layers": path_layers,
            "path_action_version": "0.1",
        },
        "hex_cluster_gravity": np.asarray(raw["hex_cluster_gravity"]).round(digits).tolist(),
        "family_multiscale_consistency": {
            str(k): round(float(v), digits) for k, v in raw["family_multiscale_consistency"].items()
        },
    }


def build_sparse_hex_scene(
    hits_by_family: list[int] | np.ndarray,
    C_F: np.ndarray,
    *,
    nh_per_family: int = 12,
    max_families: int = 40,
    params: HexOutputParams | None = None,
) -> dict[str, Any]:
    """
    Materialize hex_activation, adjacency, lifted C, R, distance, family_hex_map
    for active families (top ``max_families`` by hit count).

    Hex layout: per active family f, indices u(f,0)…u(f,nh-1) on a ring;
    activation uniform hits[f]/nh on that family’s slots.
    """
    p = params or HexOutputParams()
    h = np.asarray(hits_by_family, dtype=np.float64).reshape(-1)
    nf = int(h.shape[0])
    order = list(np.argsort(-h)[:max_families])
    active = [int(i) for i in order if h[i] > 0.0]
    if not active:
        active = [0]
        h = h.copy()
        h[0] = 1.0

    nh = int(nh_per_family)
    idx: dict[tuple[int, int], int] = {}
    u = 0
    family_hex_map: dict[int, list[int]] = {}
    for f in active:
        family_hex_map[f] = []
        for j in range(nh):
            idx[(f, j)] = u
            family_hex_map[f].append(u)
            u += 1
    N = u
    a = np.zeros(N, dtype=np.float64)
    for f in active:
        mass = float(h[f]) / nh
        for j in range(nh):
            a[idx[(f, j)]] = mass

    adj: list[list[int]] = [[] for _ in range(N)]
    for f in active:
        for j in range(nh):
            h0 = idx[(f, j)]
            h_prev = idx[(f, (j - 1) % nh)]
            h_next = idx[(f, (j + 1) % nh)]
            adj[h0].extend([h_prev, h_next])
    for i in range(N):
        adj[i] = list(dict.fromkeys(adj[i]))

    c_mat = np.zeros((N, N), dtype=np.float64)
    for f in active:
        for g in active:
            w = float(C_F[f, g]) if f < C_F.shape[0] and g < C_F.shape[1] else 0.0
            for j in range(nh):
                for k in range(nh):
                    c_mat[idx[(f, j)], idx[(g, k)]] = w
    np.fill_diagonal(c_mat, 0.0)

    resist = np.zeros(N, dtype=np.float64)
    for f in active:
        for j in range(nh):
            uu = idx[(f, j)]
            resist[uu] = 0.15 + 0.4 / (a[uu] + 0.05)

    dist = np.full((N, N), p.cross_family_distance, dtype=np.float64)
    np.fill_diagonal(dist, 0.0)
    for f in active:
        for j in range(nh):
            for k in range(nh):
                uj = idx[(f, j)]
                uk = idx[(f, k)]
                ring = min(abs(j - k), nh - abs(j - k))
                dist[uj, uk] = float(ring)

    fam_act = {f: float(h[f]) for f in active}
    return {
        "hex_activation": a,
        "adjacency": adj,
        "contradiction_matrix": c_mat,
        "resistance": resist,
        "family_hex_map": family_hex_map,
        "family_activation": fam_act,
        "distance_matrix": dist,
        "active_families": active,
    }


def attach_hex_product_outputs(
    hits_by_family: list[int] | np.ndarray,
    *,
    F: int = 288,
    nh_per_family: int = 12,
    max_families: int = 40,
    params: HexOutputParams | None = None,
    serialize: bool = True,
) -> dict[str, Any]:
    """
    Runtime hook: stub C_F from semantic field defaults; build sparse hex scene; compute outputs.

    Call after concept→family hits are known, before/ alongside family export.
    """
    from core.engine.matrix_loader import load_production_matrices

    h = list(hits_by_family[:F]) + [0] * max(0, F - len(hits_by_family))
    mats = load_production_matrices()
    C_F = np.asarray(mats["C_F"], dtype=np.float64)
    scene = build_sparse_hex_scene(
        h, C_F, nh_per_family=nh_per_family, max_families=max_families, params=params
    )
    out = compute_hex_outputs(
        scene["hex_activation"],
        scene["adjacency"],
        scene["contradiction_matrix"],
        scene["resistance"],
        scene["family_hex_map"],
        scene["family_activation"],
        scene["distance_matrix"],
        params=params,
    )
    payload: dict[str, Any] = {
        "engine": "hex_product_outputs_v1",
        "active_families": scene["active_families"],
        "n_hex_cells": int(len(scene["hex_activation"])),
    }
    if serialize:
        payload.update(serialize_hex_outputs(out))
    else:
        payload["raw"] = out
    return payload


def attach_microstructure_analytics_public(
    hits_by_family: list[int] | np.ndarray,
    *,
    F: int = 288,
    nh_per_family: int = 12,
    max_families: int = 40,
    params: HexOutputParams | None = None,
    digits: int = 6,
) -> dict[str, Any]:
    """
    Same computation as ``attach_hex_product_outputs``, but key names avoid
    ``hex`` / topology tokens so ``apply_public_projection`` retains the block.
    """
    full = attach_hex_product_outputs(
        hits_by_family,
        F=F,
        nh_per_family=nh_per_family,
        max_families=max_families,
        params=params,
        serialize=True,
    )
    fam_cap = active_family_count()  # 288 default; 240 when grain=10
    pc = full["propagation_corridors"]
    align = full["family_multiscale_consistency"]
    align_pub = {k: v for k, v in align.items() if k.isdigit() and int(k) < fam_cap}
    return {
        "engine": full["engine"],
        "active_slot_count": full["n_hex_cells"],
        "active_policy_families": [f for f in full["active_families"] if f < fam_cap],
        "area_math_grain_family_cap": fam_cap,
        "microstructure_hotspots": full["hex_hotspot_map"],
        "microstructure_tension_front": full["hex_contradiction_front"],
        "microstructure_propagation": {
            "propagated_activation": pc["hex_propagation_vector"],
            "propagation_flow_matrix": pc["propagation_flow_matrix"],
            "corridor_edges": pc["corridor_edges"],
        },
        "microstructure_gravity": full["hex_cluster_gravity"],
        "microstructure_family_alignment": align_pub,
    }
