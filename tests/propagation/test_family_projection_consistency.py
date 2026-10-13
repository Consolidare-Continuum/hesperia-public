# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Propagated family results consistent with family→area mapping and propagated area totals.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.propagation.family_projection import (
    build_family_area_projection,
    project_area_to_families,
    propagate_family_counts,
)


def test_families_per_area_sum_to_288():
    fa = np.array([f // 24 for f in range(288)], dtype=np.int64)
    per_area, _ = build_family_area_projection(fa)
    assert per_area.sum() == 288
    assert list(per_area) == [24] * 12


def test_project_area_to_families_sums_match():
    fa = np.array([f // 24 for f in range(288)], dtype=np.int64)
    area_vector = np.ones(12) / 12
    family_out = project_area_to_families(area_vector, fa)
    assert len(family_out) == 288
    assert abs(family_out.sum() - area_vector.sum()) < 1e-9


def test_each_area_mass_distributed_only_to_its_families():
    fa = np.array([f // 24 for f in range(288)], dtype=np.int64)
    area_vector = np.zeros(12)
    area_vector[3] = 1.0
    family_out = project_area_to_families(area_vector, fa)
    # Only families in area 3 (indices 72..95) get non-zero
    assert family_out[:72].sum() == 0
    assert family_out[96:].sum() == 0
    assert abs(family_out[72:96].sum() - 1.0) < 1e-9
    assert np.all(family_out[72:96] == 1.0 / 24)


def test_propagate_family_counts_derived_from_area():
    fa = np.array([f // 24 for f in range(288)], dtype=np.int64)
    area_vector = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    family_counts_input = np.ones(288) * 100  # ignored; output is area-derived
    out = propagate_family_counts(family_counts_input, area_vector, fa)
    assert abs(out.sum() - 1.0) < 1e-9
    assert out[48:72].sum() == pytest.approx(1.0)  # area 2 is index 2, families 48..71
    assert np.all(out[:48] == 0)
    assert np.all(out[72:] == 0)
