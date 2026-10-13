# HESPERIA — RAD. Ethan Phase 4 — L8 narrative cluster gravity (proxy lattice).
# ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md §H8; active chain components per area.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from hesperia.extensions.dynamics.state import (
    FAMILIES_PER_AREA,
    NUM_AREAS,
    NUM_FAMILIES,
    Phase4Theta,
)


@dataclass
class L8Cluster:
    cluster_id: str
    area: int
    f_min: int
    f_max: int
    mass: float
    density: float
    radius: float
    gravity: float
    velocity: float


def ephemeral_hex_from_hits(hits: list[int], cap: int) -> dict[str, float]:
    """Sparse x_h proxy when Phase 3 off — hit-normalized on top families."""
    h = list(hits)[:NUM_FAMILIES]
    while len(h) < NUM_FAMILIES:
        h.append(0)
    total = float(sum(h))
    if total <= 0:
        return {}
    order = sorted(range(NUM_FAMILIES), key=lambda f: (-h[f], f))[: max(1, cap)]
    return {str(f): h[f] / total for f in order if h[f] > 0}


def _consecutive_runs(sorted_fams: list[int]) -> list[list[int]]:
    if not sorted_fams:
        return []
    runs: list[list[int]] = [[sorted_fams[0]]]
    for x in sorted_fams[1:]:
        if x == runs[-1][-1] + 1:
            runs[-1].append(x)
        else:
            runs.append([x])
    return runs


def compute_l8_clusters(
    hex_x: dict[str, float],
    prev_mass: dict[str, float],
    *,
    theta: Phase4Theta | None = None,
) -> tuple[list[L8Cluster], dict[str, float]]:
    """
    Connected runs on active family-proxy chain per area → Mass, Density, Radius, Gravity, Velocity.
    """
    th = theta or Phase4Theta()
    clusters: list[L8Cluster] = []
    new_prev: dict[str, float] = {}

    for area in range(NUM_AREAS):
        lo, hi = area * FAMILIES_PER_AREA, (area + 1) * FAMILIES_PER_AREA
        fams = sorted(
            int(k)
            for k in hex_x
            if k.isdigit() and lo <= int(k) < hi and float(hex_x[k]) > 0
        )
        runs = _consecutive_runs(fams)

        for run in runs:
            mass = sum(float(hex_x[str(f)]) for f in run)
            size = len(run)
            internal = max(0, size - 1)
            density = internal / max(1, size - 1) if size > 1 else 0.5
            cen = float(sum(run)) / size
            radius = float(np.mean([abs(f - cen) for f in run])) / 12.0
            gravity = mass * (0.5 + density) / (1.0 + max(radius, 1e-9))
            cid = f"a{area}_f{run[0]}_{run[-1]}"
            vel = mass - float(prev_mass.get(cid, 0.0))
            clusters.append(
                L8Cluster(
                    cluster_id=cid,
                    area=area,
                    f_min=run[0],
                    f_max=run[-1],
                    mass=mass,
                    density=density,
                    radius=radius,
                    gravity=gravity,
                    velocity=vel,
                )
            )
            new_prev[cid] = mass

        for i in range(len(fams) - 1):
            if abs(float(hex_x[str(fams[i])]) - float(hex_x[str(fams[i + 1])])) > th.tau_front:
                pass  # front edge counted below

    return clusters, new_prev


def count_fronts_per_area(hex_x: dict[str, float]) -> list[int]:
    th = Phase4Theta()
    out = [0] * NUM_AREAS
    for area in range(NUM_AREAS):
        lo, hi = area * FAMILIES_PER_AREA, (area + 1) * FAMILIES_PER_AREA
        fams = sorted(int(k) for k in hex_x if k.isdigit() and lo <= int(k) < hi)
        for i in range(len(fams) - 1):
            if fams[i + 1] != fams[i] + 1:
                continue
            if abs(float(hex_x[str(fams[i])]) - float(hex_x[str(fams[i + 1])])) > th.tau_front:
                out[area] += 1
    return out


def apply_cluster_gravity_to_area_injection(
    injection_12: list[float],
    clusters: list[L8Cluster],
    epsilon: float,
) -> list[float]:
    if not clusters or epsilon <= 0:
        return list(injection_12)
    g = [0.0] * NUM_AREAS
    for c in clusters:
        if 0 <= c.area < NUM_AREAS:
            g[c.area] += c.gravity
    s = float(sum(g))
    if s <= 0:
        return list(injection_12)
    gn = np.array(g, dtype=np.float64) / s
    inj = np.maximum(np.asarray(injection_12, dtype=np.float64) + float(epsilon) * gn, 0.0)
    inj = inj / inj.sum() if inj.sum() > 0 else np.full(NUM_AREAS, 1.0 / NUM_AREAS)
    return [float(x) for x in inj.tolist()]


def apply_cluster_gravity_to_family_injection(
    fam_inj: list[float],
    clusters: list[L8Cluster],
    epsilon: float,
) -> list[float]:
    if not clusters or epsilon <= 0:
        return list(fam_inj)
    boost = np.zeros(NUM_FAMILIES, dtype=np.float64)
    for c in clusters:
        n = c.f_max - c.f_min + 1
        if n <= 0:
            continue
        share = c.gravity / float(n)
        for f in range(c.f_min, c.f_max + 1):
            if 0 <= f < NUM_FAMILIES:
                boost[f] += share
    bs = float(boost.sum())
    if bs <= 0:
        return list(fam_inj)
    boost = boost / bs
    inj = np.asarray(fam_inj, dtype=np.float64).reshape(NUM_FAMILIES)
    inj = np.maximum(inj + float(epsilon) * boost, 0.0)
    inj = inj / inj.sum() if inj.sum() > 0 else np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES)
    return [float(x) for x in inj.tolist()]


def clusters_to_public_rows(clusters: list[L8Cluster], limit: int = 24) -> list[dict[str, Any]]:
    ranked = sorted(clusters, key=lambda c: (-c.gravity, c.cluster_id))
    rows = []
    for c in ranked[:limit]:
        rows.append(
            {
                "id": c.cluster_id,
                "area": c.area,
                "mass": round(c.mass, 6),
                "gravity": round(c.gravity, 6),
                "velocity": round(c.velocity, 6),
            }
        )
    return rows


def field_dynamics_phase4_enabled() -> bool:
    import os

    return os.environ.get("HESPERIA_FIELD_DYNAMICS_PHASE4", "").strip().lower() in ("1", "true", "yes")
