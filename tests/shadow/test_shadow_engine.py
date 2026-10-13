# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Shadow correction engine: tail suppression, dominance reinforcement, entropy stabilization.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.shadow.engine import compute_shadow_correction
from sphere.shadow.suppression import apply_tail_suppression
from sphere.shadow.dominance_filter import apply_dominant_area_reinforcement
from sphere.shadow.entropy_correction import stabilize_entropy


def test_tail_suppression_zeros_below_threshold():
    v = np.array([0.5, 0.02, 0.3, 0.01, 0.17], dtype=np.float64)
    out, count, mass = apply_tail_suppression(v, structural_threshold=0.02)
    # Values strictly below 0.02 are zeroed (0.01); 0.02 is kept
    assert out[3] == 0
    assert out[0] == 0.5 and out[1] == 0.02 and out[2] == 0.3 and out[4] == 0.17
    assert count == 1


def test_dominance_reinforcement_boosts_dominant():
    v = np.array([0.1, 0.5, 0.2, 0.2], dtype=np.float64)
    out = apply_dominant_area_reinforcement(v, boost_factor=0.2, num_areas=4)
    assert out[1] > 0.5 / 1.0  # dominant (index 1) gets boosted then renormalized
    assert abs(out.sum() - 1.0) < 1e-9


def test_shadow_correction_returns_correct_shape():
    pv = np.ones(12) / 12
    pf = np.ones(288) / 288
    out = compute_shadow_correction(pv, pf)
    assert len(out["corrected_area_vector"]) == 12
    assert len(out["corrected_family_counts"]) == 288
    assert "shadow_diagnostics" in out
    assert "tail_suppression_count" in out["shadow_diagnostics"]
    assert "entropy_before" in out["shadow_diagnostics"]
    assert "tension_after" in out["shadow_diagnostics"]


def test_shadow_correction_reduces_entropy_on_uniform():
    # Uniform has high entropy; after dominance boost and entropy blend, entropy should drop
    pv = np.ones(12) / 12
    pf = np.ones(288) / 288
    out = compute_shadow_correction(
        pv, pf, dominance_boost_factor=0.3, entropy_blend_strength=0.4
    )
    diag = out["shadow_diagnostics"]
    assert diag["entropy_after"] <= diag["entropy_before"] + 0.01


def test_shadow_correction_preserves_dominant_influence():
    pv = np.zeros(12)
    pv[2] = 0.8
    pv[5] = 0.1
    pv[7] = 0.1
    pf = np.zeros(288)
    out = compute_shadow_correction(pv, pf, structural_threshold=0.01)
    cv = out["corrected_area_vector"]
    assert cv[2] >= 0.7  # dominant area should remain dominant after correction
