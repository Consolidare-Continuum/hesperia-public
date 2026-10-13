# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Higher stability should reduce effective diffusion (deterministic modulation).
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.propagation.weighting import (
    apply_stability_modulation,
    apply_jump_rate_modulation,
    compute_effective_diffusion_rate,
)
from sphere.propagation.engine import compute_propagation


def _ring_adjacency():
    adj = np.zeros((12, 12), dtype=np.float64)
    for i in range(12):
        adj[i, (i - 1) % 12] = 1
        adj[i, (i + 1) % 12] = 1
    return adj


def _family_to_area():
    return np.array([f // 24 for f in range(288)], dtype=np.int64)


def test_stability_reduces_effective_alpha():
    a0 = apply_stability_modulation(0.5, 0.0)
    a1 = apply_stability_modulation(0.5, 1.0)
    assert a1 < a0
    assert a0 == 0.5
    assert a1 == 0.25  # 0.5 * (1 - 0.5*1) = 0.25


def test_jump_rate_increases_effective_alpha():
    a0 = apply_jump_rate_modulation(0.5, 0.0)
    a1 = apply_jump_rate_modulation(0.5, 1.0)
    assert a1 > a0
    assert a0 == 0.5


def test_engine_uses_stability_and_jump_rate():
    adj = _ring_adjacency()
    fa = _family_to_area()
    v = np.ones(12) / 12
    out_no_mod = compute_propagation(
        v, np.zeros(288), adj, fa,
        base_alpha=0.5,
        stability_index=None,
        jump_rate=None,
    )
    out_stability = compute_propagation(
        v, np.zeros(288), adj, fa,
        base_alpha=0.5,
        stability_index=0.9,
        jump_rate=None,
    )
    # With high stability, effective alpha should be lower
    assert out_stability["propagation_diagnostics"]["diffusion_coefficient_used"] < out_no_mod["propagation_diagnostics"]["diffusion_coefficient_used"]
    assert out_stability["propagation_diagnostics"]["stability_modulation_applied"] is True
