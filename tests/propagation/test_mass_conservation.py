# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Mass conservation: total area mass before and after propagation within epsilon
unless documented normalization is applied.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.propagation.engine import compute_propagation


def _ring_adjacency() -> np.ndarray:
    adj = np.zeros((12, 12), dtype=np.float64)
    for i in range(12):
        adj[i, (i - 1) % 12] = 1
        adj[i, (i + 1) % 12] = 1
    return adj


def _family_to_area() -> np.ndarray:
    return np.array([f // 24 for f in range(288)], dtype=np.int64)


def test_mass_conserved_when_normalize_output_false():
    adj = _ring_adjacency()
    fa = _family_to_area()
    area_vector = np.zeros(12)
    area_vector[0] = 1.0
    area_vector[5] = 0.5
    family_counts = np.zeros(288)
    out = compute_propagation(
        area_vector,
        family_counts,
        adj,
        fa,
        base_alpha=0.4,
        normalize_output=False,
    )
    mass_before = sum(area_vector)
    mass_after = sum(out["propagated_area_vector"])
    assert out["propagation_diagnostics"]["conservation_ok"] is True
    assert abs(mass_after - mass_before) < 1e-5


def test_mass_after_normalization_sum_one():
    adj = _ring_adjacency()
    fa = _family_to_area()
    area_vector = np.array([0.2, 0.3, 0.1, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.03, 0.02, 0.0])
    family_counts = np.zeros(288)
    out = compute_propagation(
        area_vector,
        family_counts,
        adj,
        fa,
        base_alpha=0.5,
        normalize_output=True,
    )
    assert abs(sum(out["propagated_area_vector"]) - 1.0) < 1e-9
    assert abs(sum(out["propagated_family_counts"]) - 1.0) < 1e-8
    assert out["propagation_diagnostics"]["normalization_applied"] is True


def test_family_projection_preserves_total_mass():
    adj = _ring_adjacency()
    fa = _family_to_area()
    area_vector = np.ones(12) / 12
    family_counts = np.zeros(288)
    out = compute_propagation(
        area_vector,
        family_counts,
        adj,
        fa,
        base_alpha=0.3,
        normalize_output=False,
    )
    area_sum = sum(out["propagated_area_vector"])
    family_sum = sum(out["propagated_family_counts"])
    assert abs(family_sum - area_sum) < 1e-9
