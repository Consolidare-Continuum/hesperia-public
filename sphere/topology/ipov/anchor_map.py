# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
IPoV-01 — Geodesic sphere anchor map (frozen, v1).

Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §1.2

Area ring: 12 areas on equatorial circle of unit sphere.
Family patches: 24 families per area, 2 elevation rows of 12, ±12° from equator.
Pentagon poles: 12 icosahedron vertices (geodesic ν=85 soccer-ball poles).

Family geodesic hex allocation rule (§1.2.1):
  - 240 families → 251 geodesic hex slots each  (family_index_in_area % 6 != 0)
  - 48 families  → 250 geodesic hex slots each  (family_index_in_area % 6 == 0)
  - Check: 240×251 + 48×250 = 72,240  ✓
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Area ring — canonical order (from hex_sphere_areas_families_ideal_proportions.csv)
# ---------------------------------------------------------------------------

AREA_RING: list[str] = [
    "GOOD",          # area_id 0
    "HARM",          # area_id 1
    "TRUTH",         # area_id 2
    "DECEIT",        # area_id 3
    "ORDER",         # area_id 4
    "CHAOS",         # area_id 5
    "FREEDOM",       # area_id 6
    "CONTROL",       # area_id 7
    "CARE",          # area_id 8
    "INDIFFERENCE",  # area_id 9
    "CREATION",      # area_id 10
    "DESTRUCTION",   # area_id 11
]

# ---------------------------------------------------------------------------
# Geodesic sphere constants (ν=85, GCS_NU85)
# ---------------------------------------------------------------------------


class GeodesicConstants(NamedTuple):
    """Frozen geodesic sphere parameters. Spec §1.2."""

    frequency_nu: int = 85
    hex_count: int = 72_240          # 10ν² − 10
    pentagon_count: int = 12
    total_faces: int = 72_252        # 72240 + 12
    semantic_hex_count: int = 72_000 # 12 × 24 × 250
    delta_hex: int = 240             # geodesic − semantic
    sides_count: int = 433_440       # 72240 × 6
    semantic_sides_count: int = 432_000
    delta_sides: int = 1_440
    scale_factor_sigma: float = 1.003_333_333_3   # 72240 / 72000
    mean_hex_per_family: float = 250.833_333_333_3 # 72240 / 288
    mean_hex_per_area: int = 6_020
    families_251: int = 240
    families_250: int = 48
    extra_hex_per_pentagon_zone: int = 20

GCS = GeodesicConstants()

# METRIC-19 — canonical id shared with hesperia/schemas/anchor_map_v1.json
ANCHOR_MAP_ID = "anchor_map_v1"


def geodesic_hex_count_for_family(family_index_in_area: int) -> int:
    """Return 250 or 251 for a family given its 0-based index within its area."""
    return 250 if family_index_in_area % 6 == 0 else 251


# ---------------------------------------------------------------------------
# Direction vector helpers
# ---------------------------------------------------------------------------

Vec3 = tuple[float, float, float]


def _normalize(v: Vec3) -> Vec3:
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _sphere_dir(azimuth_rad: float, elevation_rad: float) -> Vec3:
    """Convert (azimuth, elevation) angles to unit direction vector."""
    cos_el = math.cos(elevation_rad)
    return (
        cos_el * math.cos(azimuth_rad),
        cos_el * math.sin(azimuth_rad),
        math.sin(elevation_rad),
    )


# ---------------------------------------------------------------------------
# Area anchor directions
# ---------------------------------------------------------------------------

def _area_directions() -> list[Vec3]:
    """12 area anchor directions on the equatorial ring (elevation=0)."""
    dirs = []
    for i in range(12):
        az = 2.0 * math.pi * i / 12.0
        dirs.append(_sphere_dir(az, 0.0))
    return dirs


# ---------------------------------------------------------------------------
# Family anchor directions
# ---------------------------------------------------------------------------

_FAMILY_ELEVATION_DEG = 12.0   # ±12° elevation for two rows

def _family_directions() -> list[list[Vec3]]:
    """
    288 family anchor directions, indexed [area_idx][family_idx_in_area].

    Layout within each area wedge (30° arc):
    - Row 0 (family_index 0..11):  elevation = +FAMILY_ELEVATION_DEG
    - Row 1 (family_index 12..23): elevation = -FAMILY_ELEVATION_DEG
    - Columns 0..11: evenly spread across ±FAMILY_COL_SPREAD_DEG around area center
    """
    el_rad = math.radians(_FAMILY_ELEVATION_DEG)
    col_spread_rad = math.radians(12.5)  # total spread = 25° / 2 per side
    dirs_per_area: list[list[Vec3]] = []
    for i in range(12):
        area_az = 2.0 * math.pi * i / 12.0
        area_dirs: list[Vec3] = []
        for j in range(24):
            row = j // 12
            col = j % 12
            azimuth_offset = (col - 5.5) * (2.0 * col_spread_rad / 11.0)
            az = area_az + azimuth_offset
            el = el_rad if row == 0 else -el_rad
            area_dirs.append(_sphere_dir(az, el))
        dirs_per_area.append(area_dirs)
    return dirs_per_area


# ---------------------------------------------------------------------------
# Pentagon pole directions (12 icosahedron vertices)
# ---------------------------------------------------------------------------

def _pentagon_poles() -> list[Vec3]:
    """
    12 pentagon pole directions — icosahedron vertices normalized to unit sphere.
    Geodesic sphere (ν=85) soccer-ball pentagons sit at these 12 poles.
    """
    phi = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio ≈ 1.618
    raw: list[Vec3] = [
        (0.0, +1.0, +phi), (0.0, +1.0, -phi),
        (0.0, -1.0, +phi), (0.0, -1.0, -phi),
        (+1.0, +phi, 0.0), (+1.0, -phi, 0.0),
        (-1.0, +phi, 0.0), (-1.0, -phi, 0.0),
        (+phi, 0.0, +1.0), (+phi, 0.0, -1.0),
        (-phi, 0.0, +1.0), (-phi, 0.0, -1.0),
    ]
    return [_normalize(v) for v in raw]


# ---------------------------------------------------------------------------
# AnchorMap — frozen v1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnchorMap:
    """
    Frozen anchor map v1.  Built once; reused across sessions.

    area_directions[i]          : unit Vec3 for area ring index i (0..11)
    family_directions[i][j]     : unit Vec3 for area i, family j within area (0..23)
    pentagon_directions[p]      : unit Vec3 for pentagon pole p (0..11)
    global_family_id(i, j)      : 0-based global family index (0..287)
    family_geodesic_hex_count(i, j): 250 or 251 per §1.2.1
    """

    area_directions: tuple[Vec3, ...]
    family_directions: tuple[tuple[Vec3, ...], ...]
    pentagon_directions: tuple[Vec3, ...]
    geodesic: GeodesicConstants = field(default_factory=GeodesicConstants)

    def area_id_to_index(self, area_id: str) -> int:
        return AREA_RING.index(area_id)

    def global_family_id(self, area_idx: int, family_idx_in_area: int) -> int:
        return area_idx * 24 + family_idx_in_area

    def area_family_from_global(self, global_id: int) -> tuple[int, int]:
        return global_id // 24, global_id % 24

    def family_geodesic_hex_count(self, area_idx: int, family_idx_in_area: int) -> int:
        return geodesic_hex_count_for_family(family_idx_in_area)

    def area_direction(self, area_id: str) -> Vec3:
        return self.area_directions[self.area_id_to_index(area_id)]

    def family_direction(self, area_id: str, family_idx_in_area: int) -> Vec3:
        return self.family_directions[self.area_id_to_index(area_id)][family_idx_in_area]


def build_anchor_map() -> AnchorMap:
    """Build and return the frozen anchor_map_v1. Pure; no I/O."""
    area_dirs = tuple(_area_directions())
    fam_dirs = tuple(tuple(row) for row in _family_directions())
    pent_dirs = tuple(_pentagon_poles())
    return AnchorMap(
        area_directions=area_dirs,
        family_directions=fam_dirs,
        pentagon_directions=pent_dirs,
        geodesic=GeodesicConstants(),
    )


# Module-level singleton — import and reuse
ANCHOR_MAP: AnchorMap = build_anchor_map()
