# HESPERIA — minimal IPoW support for GTP-04 (PointZeroDelta).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
`InteriorPointOfWorldView` (IPoW) per
docs/brain-export/operational/assignments/HESPERIA-FORMALIZATION-GEODESIC-SPHERE-AND-INTERIOR-POINT-OF-WORLD-VIEW-v0_1.md
§7 (22_SPEC__), scoped to exactly what GTP-04 needs: PointZero default and
PointZeroDelta. Full IPoW (GCS distance tiers, anchor_map_v1 embedding) is separately
gated — 22_SPEC §12: "Implement anchor_map_v1 + IPoW only after operator approves
implementation wave" — and is METRIC-23 (deferred) in release/v0.7.0/RELEASE_SCOPE.md.
This module does not claim that broader scope; it is the narrow slice GTP-04 depends on.
"""

from __future__ import annotations

from dataclasses import dataclass

Vec3 = tuple[float, float, float]

POINT_ZERO: Vec3 = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class InteriorPointOfWorldView:
    """Spec §7.1 fields, PointZero-scoped subset."""

    powv_position: Vec3 = POINT_ZERO
    powv_step: int = 0
    powv_point_zero: bool = True
    powv_update_mode: str = "point_zero"


def point_zero() -> InteriorPointOfWorldView:
    """Spec §7.2 normative default: new session/iteration/reset state."""
    return InteriorPointOfWorldView()


def point_zero_delta(r_t: Vec3, r_zero: Vec3 = POINT_ZERO) -> Vec3:
    """delta_powv_t = r_t - r_zero. Spec §9.1."""
    return (r_t[0] - r_zero[0], r_t[1] - r_zero[1], r_t[2] - r_zero[2])


def step_delta(r_t: Vec3, r_prev: Vec3) -> Vec3:
    """Optional step-to-step variant: delta_powv_step_t = r_t - r_{t-1}. Spec §9.1."""
    return point_zero_delta(r_t, r_prev)
