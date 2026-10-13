# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
IPoV-02 / IPoV-03 — Interior Point of World View (PoWV)

Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §2–5

PoWV = one observer position inside the unit ball Ω.
Surface anchors (areas, families, pentagons) lie on ∂Ω.
Distance field is always Euclidean chord: d_a = ‖r − s_a‖.

compute_powv_step() is a pure function: same inputs → same outputs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .anchor_map import ANCHOR_MAP, AREA_RING, AnchorMap, Vec3, GeodesicConstants

# ---------------------------------------------------------------------------
# Pydantic output schema — interior_point_of_world_view_v1
# ---------------------------------------------------------------------------


class PoWVGeodesicSphere(BaseModel):
    """Frozen geodesic constants embedded in every PoWV output. Spec §5.1."""

    canonical: bool = True
    frequency_nu: int = 85
    hex_count: int = 72_240
    pentagon_count: int = 12
    total_faces: int = 72_252
    semantic_hex_count: int = 72_000
    delta_hex: int = 240
    sides_count: int = 433_440
    semantic_sides_count: int = 432_000
    delta_sides: int = 1_440
    scale_factor_sigma: float = 1.003_333_333_3
    mean_hex_per_family: float = 250.833_333_333_3
    mean_hex_per_area: int = 6_020
    families_251: int = 240
    families_250: int = 48
    extra_hex_per_pentagon_zone: int = 20


class DistanceEntry(BaseModel):
    """Distance from PoWV to one anchor on ∂Ω."""

    anchor_type: str       # "area" | "family" | "pentagon"
    anchor_id: str         # area_id, "global:{n}", or "pentagon:{n}"
    area_id: str = ""      # for family and area entries
    global_id: int = -1    # 0-based global family index; -1 for areas/pentagons
    d: float               # Euclidean chord distance
    d_relative: float      # d / sum(d) over all anchors at same tier


class PoWVCoupling(BaseModel):
    last_surface_step: int = 0
    guard_events_count: int = 0
    shadow_applied: bool = False


class PoWVProvenance(BaseModel):
    update_mode: str = "point_zero"   # "point_zero" | "surface_event" | "direct_set"
    lambda_gain: float = 0.10
    distance_metric: str = "chord"
    geodesic_ref: str = "SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §1.2"


class InteriorPointOfWorldView(BaseModel):
    """
    Schema: interior_point_of_world_view_v1.
    Spec §5.1.
    """

    schema_name: str = Field(default="interior_point_of_world_view_v1", alias="schema")
    system_version: str = ""
    step: int = 0
    point_zero: bool = True

    r_x: float = Field(default=0.0, alias="r_x")
    r_y: float = Field(default=0.0, alias="r_y")
    r_z: float = Field(default=0.0, alias="r_z")

    ellipsoid_a: float = 1.0
    ellipsoid_b: float = 1.0
    ellipsoid_c: float = 1.0

    geodesic_sphere: PoWVGeodesicSphere = Field(default_factory=PoWVGeodesicSphere)

    area_distances: list[DistanceEntry] = Field(default_factory=list)
    family_distances: list[DistanceEntry] = Field(default_factory=list)
    pentagon_distances: list[DistanceEntry] = Field(default_factory=list)

    barycentric_areas: list[float] = Field(default_factory=list)

    coupling: PoWVCoupling = Field(default_factory=PoWVCoupling)
    provenance: PoWVProvenance = Field(default_factory=PoWVProvenance)

    model_config = {"populate_by_name": True}

    def r(self) -> Vec3:
        return (self.r_x, self.r_y, self.r_z)

    def r_norm(self) -> float:
        return math.sqrt(self.r_x ** 2 + self.r_y ** 2 + self.r_z ** 2)


# ---------------------------------------------------------------------------
# Internal state (mutable, not Pydantic — for computation)
# ---------------------------------------------------------------------------


@dataclass
class PoWVState:
    """
    Mutable interior state for iterative PoWV computation.
    Converted to InteriorPointOfWorldView for export.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    step: int = 0
    update_mode: str = "point_zero"
    lambda_gain: float = 0.10
    guard_events_count: int = 0
    shadow_applied: bool = False

    def r(self) -> Vec3:
        return (self.x, self.y, self.z)

    def norm(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def clamp_to_unit_ball(self) -> None:
        n = self.norm()
        if n > 1.0:
            self.x /= n
            self.y /= n
            self.z /= n


# ---------------------------------------------------------------------------
# Distance computation
# ---------------------------------------------------------------------------


def _chord(r: Vec3, s: Vec3) -> float:
    return math.sqrt(
        (r[0] - s[0]) ** 2 + (r[1] - s[1]) ** 2 + (r[2] - s[2]) ** 2
    )


def _compute_distances(
    r: Vec3,
    anchor_map: AnchorMap,
) -> tuple[list[DistanceEntry], list[DistanceEntry], list[DistanceEntry]]:
    """Return (area_distances, family_distances, pentagon_distances)."""

    # Areas
    area_ds = [_chord(r, anchor_map.area_directions[i]) for i in range(12)]
    area_sum = sum(area_ds) + 1e-12
    area_entries = [
        DistanceEntry(
            anchor_type="area",
            anchor_id=AREA_RING[i],
            area_id=AREA_RING[i],
            global_id=-1,
            d=area_ds[i],
            d_relative=area_ds[i] / area_sum,
        )
        for i in range(12)
    ]

    # Families (288 total)
    fam_ds = []
    for i in range(12):
        for j in range(24):
            fam_ds.append(_chord(r, anchor_map.family_directions[i][j]))
    fam_sum = sum(fam_ds) + 1e-12
    family_entries = [
        DistanceEntry(
            anchor_type="family",
            anchor_id=f"global:{i * 24 + j}",
            area_id=AREA_RING[i],
            global_id=i * 24 + j,
            d=fam_ds[i * 24 + j],
            d_relative=fam_ds[i * 24 + j] / fam_sum,
        )
        for i in range(12)
        for j in range(24)
    ]

    # Pentagons (12)
    pent_ds = [_chord(r, anchor_map.pentagon_directions[p]) for p in range(12)]
    pent_sum = sum(pent_ds) + 1e-12
    pentagon_entries = [
        DistanceEntry(
            anchor_type="pentagon",
            anchor_id=f"pentagon:{p}",
            area_id="",
            global_id=-1,
            d=pent_ds[p],
            d_relative=pent_ds[p] / pent_sum,
        )
        for p in range(12)
    ]

    return area_entries, family_entries, pentagon_entries


def _barycentric_areas(r: Vec3, anchor_map: AnchorMap) -> list[float]:
    """
    Area ring barycentric weights for fast area-only views.
    Uses dot-product proximity (1 − d_a / 2) normalized to sum=1.
    """
    raw = []
    for i in range(12):
        s = anchor_map.area_directions[i]
        dot = r[0] * s[0] + r[1] * s[1] + r[2] * s[2]
        raw.append(max(0.0, 1.0 + dot))  # ∈ [0,2]; higher = closer
    total = sum(raw) + 1e-12
    return [w / total for w in raw]


# ---------------------------------------------------------------------------
# IPoV-03 — compute_powv_step (pure function)
# ---------------------------------------------------------------------------


def compute_powv_step(
    state: PoWVState,
    event_vectors: list[tuple[Vec3, float]],  # list of (anchor_direction, weight)
    anchor_map: AnchorMap | None = None,
    system_version: str = "",
) -> tuple[PoWVState, InteriorPointOfWorldView]:
    """
    Pure PoWV update function.
    Spec §4.2 update law:
      r_{t+1} = normalize((1-λ)·r_t + λ·Σ w_e·s_e)

    Args:
        state: Current PoWV state (not mutated; a new state is returned).
        event_vectors: List of (surface_anchor_direction, weight) pairs.
                       weight < 0 applies an inward (penalty) pull.
        anchor_map: Use ANCHOR_MAP singleton if None.
        system_version: Optional version string embedded in output schema.

    Returns:
        (new_state, snapshot)  — new_state is a fresh PoWVState.
    """
    am = anchor_map or ANCHOR_MAP
    new_state = PoWVState(
        x=state.x,
        y=state.y,
        z=state.z,
        step=state.step + 1,
        lambda_gain=state.lambda_gain,
        guard_events_count=state.guard_events_count,
        shadow_applied=state.shadow_applied,
    )

    if event_vectors:
        lam = new_state.lambda_gain
        # Weighted sum of anchor directions
        pull_x = sum(w * s[0] for s, w in event_vectors)
        pull_y = sum(w * s[1] for s, w in event_vectors)
        pull_z = sum(w * s[2] for s, w in event_vectors)
        # Normalize pull
        pull_n = math.sqrt(pull_x ** 2 + pull_y ** 2 + pull_z ** 2)
        if pull_n > 1e-12:
            pull_x /= pull_n
            pull_y /= pull_n
            pull_z /= pull_n
        # Update law
        new_state.x = (1.0 - lam) * new_state.x + lam * pull_x
        new_state.y = (1.0 - lam) * new_state.y + lam * pull_y
        new_state.z = (1.0 - lam) * new_state.z + lam * pull_z
        new_state.clamp_to_unit_ball()
        new_state.update_mode = "surface_event"
    else:
        new_state.update_mode = state.update_mode  # no events → mode unchanged

    r = new_state.r()
    area_d, fam_d, pent_d = _compute_distances(r, am)
    bary = _barycentric_areas(r, am)

    is_point_zero = (new_state.x == 0.0 and new_state.y == 0.0 and new_state.z == 0.0)

    snapshot = InteriorPointOfWorldView(
        schema_name="interior_point_of_world_view_v1",
        system_version=system_version,
        step=new_state.step,
        point_zero=is_point_zero,
        r_x=new_state.x,
        r_y=new_state.y,
        r_z=new_state.z,
        area_distances=area_d,
        family_distances=fam_d,
        pentagon_distances=pent_d,
        barycentric_areas=bary,
        coupling=PoWVCoupling(
            last_surface_step=new_state.step,
            guard_events_count=new_state.guard_events_count,
            shadow_applied=new_state.shadow_applied,
        ),
        provenance=PoWVProvenance(
            update_mode=new_state.update_mode,
            lambda_gain=new_state.lambda_gain,
        ),
    )
    return new_state, snapshot


def powv_point_zero(
    anchor_map: AnchorMap | None = None,
    system_version: str = "",
) -> tuple[PoWVState, InteriorPointOfWorldView]:
    """Return the default point-zero PoWV (r = (0,0,0)). Spec §2.2."""
    am = anchor_map or ANCHOR_MAP
    state = PoWVState()
    return compute_powv_step(state, event_vectors=[], anchor_map=am, system_version=system_version)
