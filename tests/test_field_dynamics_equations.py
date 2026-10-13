# HESPERIA — RAD. Canonical semantic field equations (equations.py).

from __future__ import annotations

import numpy as np

from hesperia.extensions.dynamics.equations import (
    SemanticFieldParams,
    aggregate_family_to_area,
    build_contradiction_matrix,
    build_family_laplacian,
    build_resistance_matrix,
    compute_energy,
    step_field,
)


def test_build_family_laplacian_simple():
    w = np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ]
    )
    l = build_family_laplacian(w)
    expected = np.array(
        [
            [1.0, -1.0],
            [-1.0, 1.0],
        ]
    )
    assert np.allclose(l, expected)


def test_step_field_basic_shape_and_bounds():
    params = SemanticFieldParams(
        alpha=0.1,
        beta=0.05,
        gamma=0.2,
        delta=0.3,
        dt=1.0,
        epsilon=1e-9,
        tau=1e-9,
        clip_mode=True,
    )

    f = np.array([0.2, 0.8], dtype=float)
    s = np.array([0.5, 0.0], dtype=float)

    l = build_family_laplacian(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ]
    )
    r = build_resistance_matrix([0.1, 0.2])
    c = build_contradiction_matrix(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ]
    )

    result = step_field(f, s, l, r, c, params)

    assert result.field_prev.shape == (2,)
    assert result.field_next.shape == (2,)
    assert np.all(result.field_next >= 0.0)
    assert np.all(result.field_next <= 1.0)


def test_energy_returns_scalar():
    params = SemanticFieldParams(alpha=0.1, beta=0.1, gamma=0.1, delta=0.1)
    f = np.array([0.5, 0.25], dtype=float)
    s = np.array([0.3, 0.1], dtype=float)
    l = build_family_laplacian([[0.0, 1.0], [1.0, 0.0]])
    r = build_resistance_matrix([0.2, 0.4])
    c = build_contradiction_matrix([[0.0, 0.5], [0.5, 0.0]])

    e = compute_energy(f, s, l, r, c, params)
    assert isinstance(e, float)


def test_aggregate_family_to_area():
    family_field = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    family_to_area = np.array([0, 0, 1, 1], dtype=int)
    area_field = aggregate_family_to_area(family_field, family_to_area, area_count=2)
    assert np.allclose(area_field, np.array([3.0, 7.0]))
