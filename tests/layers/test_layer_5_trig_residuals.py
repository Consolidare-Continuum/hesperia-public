# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""HES-MATH-BEHAV-60..62 — L5 trig/metric residual live fill (38_SPEC)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.layers.layer_5 import EPS, compute_L5


def _base_l1_l4() -> tuple[dict, dict]:
    l1 = {"DOMINANT_AREA_ID": 0}
    l4 = {
        "INTEGRITY_CHECK_PASS_RATIO": 1.0,
        "EVIDENCE_SUPPORT_INDEX_BASELINE": 0.5,
    }
    return l1, l4


def test_l5_default_orthonormal_residuals_near_zero() -> None:
    """Default [1,0]/[0,1] pair: all residuals ≤ EPS and REALITY_GATE_TRIG True."""
    l1, l4 = _base_l1_l4()
    out = compute_L5(l1, l4, R_pos=[], R_neg=[])
    for key in (
        "LAW_OF_COSINES_RESIDUAL",
        "ROTATION_NORM_PRESERVATION_RESIDUAL",
        "ORTHONORMALITY_RESIDUAL_FROBENIUS",
        "METRIC_SYMMETRY_RESIDUAL",
        "METRIC_IDENTITY_RESIDUAL",
        "SIN_COS_IDENTITY_RESIDUAL",
    ):
        assert out[key] <= EPS, f"{key}={out[key]}"
    assert out["TRIANGLE_INEQUALITY_VIOLATION_COUNT"] == 0
    assert out["REALITY_GATE_TRIG"] is True


def test_l5_law_of_cosines_matches_38_spec() -> None:
    """‖v−w‖² ≈ ‖v‖² + ‖w‖² − 2‖v‖‖w‖cos θ for a non-orthogonal pair."""
    l1, l4 = _base_l1_l4()
    v, w = [3.0, 0.0], [1.0, 1.0]
    out = compute_L5(l1, l4, R_pos=[], R_neg=[], v=v, w=w)
    assert out["LAW_OF_COSINES_RESIDUAL"] <= EPS
    assert out["TRIANGLE_INEQUALITY_VIOLATION_COUNT"] == 0
    assert out["REALITY_GATE_TRIG"] is True


def test_l5_metric_symmetry_and_identity_live() -> None:
    """d(v,w)=d(w,v); d(x,x)=0 — not hardcoded constants."""
    l1, l4 = _base_l1_l4()
    out = compute_L5(l1, l4, R_pos=[], R_neg=[], v=[2.0, 1.0, 0.5], w=[-1.0, 0.0, 3.0])
    assert out["METRIC_SYMMETRY_RESIDUAL"] <= EPS
    assert out["METRIC_IDENTITY_RESIDUAL"] <= EPS
    # Rotation by θ preserves 2D projection norm of v.
    assert out["ROTATION_NORM_PRESERVATION_RESIDUAL"] <= EPS
    assert out["ORTHONORMALITY_RESIDUAL_FROBENIUS"] <= 1e-12
    assert out["REALITY_GATE_TRIG"] is True


def test_l5_rotation_orthonormality_identity_exact() -> None:
    """RᵀR − I Frobenius residual is numerically ~0 for any θ from v,w."""
    l1, l4 = _base_l1_l4()
    out = compute_L5(l1, l4, R_pos=[], R_neg=[], v=[1.0, 2.0], w=[2.0, -1.0])
    assert out["ORTHONORMALITY_RESIDUAL_FROBENIUS"] < 1e-12
    theta = math.acos(
        max(
            -1.0,
            min(
                1.0,
                (1.0 * 2.0 + 2.0 * -1.0)
                / (math.hypot(1.0, 2.0) * math.hypot(2.0, -1.0) + EPS),
            ),
        )
    )
    assert abs(math.sin(theta) ** 2 + math.cos(theta) ** 2 - 1.0) <= EPS
    assert out["SIN_COS_IDENTITY_RESIDUAL"] <= EPS
