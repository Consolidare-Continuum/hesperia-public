# HESPERIA — Hex-causal product signals (Task 2).

from __future__ import annotations

import numpy as np
import pytest

from core.engine.product_signals import (
    compute_product_signals,
    contradiction_pressure_hex,
    narrative_hotspot_mean_hex,
    propagation_strength_hex,
)


def test_empty_hex_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="hex layer required"):
        compute_product_signals(np.zeros((0, 3)), np.zeros((0, 3)), C_F=np.zeros((0, 0)))


def test_contradiction_uses_gram_not_family_mass() -> None:
    """Hex-row inner products must differ from fᵀ C f for structured A_hex."""
    nf, nh = 4, 3
    A = np.zeros((nf, nh))
    A[0] = [1.0, 0.0, 0.0]
    A[1] = [0.0, 1.0, 0.0]
    C = np.zeros((nf, nf))
    C[0, 1] = C[1, 0] = 1.0
    p_hex = contradiction_pressure_hex(A, C)
    f = A.sum(axis=1)
    p_f = float(f @ (C @ f))
    assert p_hex == 0.0
    assert p_f == 2.0
    assert abs(p_hex - p_f) > 1e-6


def test_propagation_strength_hex_zero_when_identical() -> None:
    A = np.ones((5, 4)) * 0.1
    assert propagation_strength_hex(A, A.copy(), dt=1.0) == 0.0


def test_hotspot_ring_includes_neighbors() -> None:
    A = np.zeros((2, 3))
    A[0, 0] = 1.0
    A[0, 1] = 1.0
    m = narrative_hotspot_mean_hex(A, lam=0.45)
    assert m > 0


def test_compute_product_signals_requires_matching_shapes() -> None:
    a0 = np.ones((3, 4))
    a1 = np.ones((3, 5))
    with pytest.raises(ValueError, match="same shape"):
        compute_product_signals(a0, a1, C_F=np.zeros((3, 3)))
