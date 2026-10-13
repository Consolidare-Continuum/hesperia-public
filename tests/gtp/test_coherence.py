# GTP-04 — PointZeroDelta broadcast + CoherenceField Psi.

from __future__ import annotations

import math

from sphere.topology.gtp.coherence import (
    NUM_AREAS,
    NUM_FAMILIES,
    VECTOR_DIM,
    broadcast,
    coherence_scalar,
    compute_coherence_field,
    get_area_anchor_directions,
    get_family_anchor_directions,
)
from sphere.topology.gtp.ipow import POINT_ZERO, point_zero_delta


def test_vector_dim_is_300() -> None:
    assert VECTOR_DIM == 12 + 288 == 300
    assert NUM_AREAS == 12
    assert NUM_FAMILIES == 288


def test_area_anchor_directions_are_unit_vectors() -> None:
    anchors = get_area_anchor_directions()
    assert len(anchors) == 12
    for v in anchors.values():
        norm = math.sqrt(sum(c * c for c in v))
        assert math.isclose(norm, 1.0, abs_tol=1e-9)


def test_family_anchor_directions_cover_all_288() -> None:
    anchors = get_family_anchor_directions()
    assert set(anchors.keys()) == set(range(288))
    for v in anchors.values():
        norm = math.sqrt(sum(c * c for c in v))
        assert math.isclose(norm, 1.0, abs_tol=1e-9)


def test_broadcast_at_point_zero_is_all_zero() -> None:
    delta = point_zero_delta(POINT_ZERO)
    deltas = broadcast(delta)
    assert all(v == 0.0 for v in deltas.values())


def test_broadcast_nonzero_delta_varies_by_anchor() -> None:
    delta = point_zero_delta((0.3, -0.2, 0.15))
    deltas = broadcast(delta)
    assert len(deltas) == 12 + 288
    assert any(v != 0.0 for v in deltas.values())


def test_compute_coherence_field_deterministic() -> None:
    delta = point_zero_delta((0.3, -0.2, 0.15))
    psi1 = compute_coherence_field(delta)
    psi2 = compute_coherence_field(delta)
    assert psi1 == psi2
    assert len(psi1.vector) == 300


def test_coherence_scalar_zero_at_point_zero() -> None:
    delta = point_zero_delta(POINT_ZERO)
    psi = compute_coherence_field(delta)
    assert coherence_scalar(psi) == 0.0
