# HESPERIA — GTP-04: PointZeroDelta broadcast + CoherenceField Psi.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""
Spec §9 (23_SPEC__): broadcast delta_powv to every area/family anchor, then aggregate
into one coherence object Psi (vector + scalar summaries) that steers GTPA (sphere/topology/gtp/gtpa.py).

Anchor directions: the 12 area anchors reuse the real, existing, deterministic
icosahedral embedding (`sphere.topology.embedding.get_aligned_area_coordinates`) —
no new area geometry invented here. The 288 family anchors have no canonical embedding
yet (22_SPEC §12: anchor_map_v1 is a separate, operator-gated implementation wave), so
each family anchor is derived deterministically from its parent area's real vertex
plus a small in-tangent-plane offset keyed by `family_index_in_area` (0..23), then
renormalized to the unit sphere. This is a provisional, fully deterministic stand-in —
documented here, not presented as the frozen `anchor_map_v1` geometry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sphere.topology.embedding import get_aligned_area_coordinates
from sphere.topology.gtp.ipow import Vec3
from core.math.entropy_metrics import compute_entropy_nats
from core.topology.invariant_catalog import (
    AREAS as NUM_AREAS,
    FAMILIES_PER_AREA,
    TOTAL_FAMILIES as NUM_FAMILIES,
)

VECTOR_DIM = NUM_AREAS + NUM_FAMILIES  # 300, spec §9.2


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(v: Vec3) -> Vec3:
    n = math.sqrt(_dot(v, v))
    if n == 0.0:
        return (0.0, 0.0, 1.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _tangent_basis(anchor: Vec3) -> tuple[Vec3, Vec3]:
    """Two unit vectors orthogonal to `anchor`, deterministic for any unit anchor."""
    ref = (0.0, 0.0, 1.0) if abs(anchor[2]) < 0.9 else (1.0, 0.0, 0.0)
    # u = anchor x ref, v = anchor x u  (both normalized)
    ux = anchor[1] * ref[2] - anchor[2] * ref[1]
    uy = anchor[2] * ref[0] - anchor[0] * ref[2]
    uz = anchor[0] * ref[1] - anchor[1] * ref[0]
    u = _normalize((ux, uy, uz))
    vx = anchor[1] * u[2] - anchor[2] * u[1]
    vy = anchor[2] * u[0] - anchor[0] * u[2]
    vz = anchor[0] * u[1] - anchor[1] * u[0]
    v = _normalize((vx, vy, vz))
    return u, v


def get_area_anchor_directions() -> dict[int, Vec3]:
    """12 real area anchors, area_id 0..11, from the canonical icosahedral embedding."""
    coords = get_aligned_area_coordinates()
    return {area_id: tuple(coords[area_id]) for area_id in range(NUM_AREAS)}


def get_family_anchor_directions() -> dict[int, Vec3]:
    """
    288 provisional family anchors, global_id 0..287 (area_id * 24 + family_index_in_area).
    Small deterministic tangent-plane offset per family index around its area's real vertex.
    """
    area_anchors = get_area_anchor_directions()
    offset_scale = 0.15  # small perturbation; keeps family anchors close to their area
    out: dict[int, Vec3] = {}
    for area_id in range(NUM_AREAS):
        anchor = area_anchors[area_id]
        u, v = _tangent_basis(anchor)
        for family_index in range(FAMILIES_PER_AREA):
            angle = 2.0 * math.pi * family_index / FAMILIES_PER_AREA
            perturbed = (
                anchor[0] + offset_scale * (math.cos(angle) * u[0] + math.sin(angle) * v[0]),
                anchor[1] + offset_scale * (math.cos(angle) * u[1] + math.sin(angle) * v[1]),
                anchor[2] + offset_scale * (math.cos(angle) * u[2] + math.sin(angle) * v[2]),
            )
            global_id = area_id * FAMILIES_PER_AREA + family_index
            out[global_id] = _normalize(perturbed)
    return out


def broadcast(delta_powv: Vec3) -> dict[str, float]:
    """
    delta_k = dot(delta_powv, s_k) for every area + family anchor. Spec §9.1.
    Keys: "area:{0..11}", "family:{0..287}".
    """
    out: dict[str, float] = {}
    for area_id, anchor in get_area_anchor_directions().items():
        out[f"area:{area_id}"] = _dot(delta_powv, anchor)
    for global_id, anchor in get_family_anchor_directions().items():
        out[f"family:{global_id}"] = _dot(delta_powv, anchor)
    return out


@dataclass(frozen=True)
class CoherenceField:
    """Psi — "one big variable". Spec §9.2."""

    vector: tuple[float, ...]  # dim 300: 12 areas then 288 families, in id order
    psi_abs: float
    psi_ent: float
    psi_align: float


def compute_coherence_field(delta_powv: Vec3) -> CoherenceField:
    """Psi_k = delta_k; Psi_abs = ||delta_powv||; Psi_ent = entropy(|delta_k|); Psi_align = max-min."""
    deltas = broadcast(delta_powv)
    vector = tuple(deltas[f"area:{i}"] for i in range(NUM_AREAS)) + tuple(
        deltas[f"family:{j}"] for j in range(NUM_FAMILIES)
    )
    psi_abs = math.sqrt(sum(d * d for d in delta_powv))
    abs_vals = [abs(x) for x in vector]
    psi_ent = compute_entropy_nats(abs_vals)
    psi_align = (max(vector) - min(vector)) if vector else 0.0
    return CoherenceField(vector=vector, psi_abs=psi_abs, psi_ent=psi_ent, psi_align=psi_align)


def coherence_scalar(
    psi: CoherenceField,
    *,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
) -> float:
    """
    C_t = alpha*Psi_abs + beta*Psi_align - gamma*variance(delta_family). Spec §9.2.
    Coefficients default to 1.0 pending `gtp_coherence_v0_1.json` calibration (spec note, §9.2).
    """
    family_deltas = psi.vector[NUM_AREAS:]
    mean = sum(family_deltas) / len(family_deltas)
    variance = sum((d - mean) ** 2 for d in family_deltas) / len(family_deltas)
    return alpha * psi.psi_abs + beta * psi.psi_align - gamma * variance
