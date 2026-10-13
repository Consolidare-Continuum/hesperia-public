# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for propagation metrics: meta_flow_ratio, normalize_weights."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_meta_flow_ratio_bounds() -> None:
    """meta_flow_ratio returns value in [0, 1] for row-stochastic W."""
    from sphere.propagation.metrics import meta_flow_ratio
    from sphere.topology import META_AREA_INDICES

    W = np.ones((12, 12)) / 12  # uniform row-stochastic
    r = meta_flow_ratio(W, META_AREA_INDICES)
    assert 0 <= r <= 1, f"meta_flow_ratio must be in [0,1], got {r}"


def test_normalize_weights_row_sum_one() -> None:
    """normalize_weights produces rows that sum to 1 (or 0)."""
    from sphere.propagation.weighting import normalize_weights

    W = np.array([[1.0, 2.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64)
    out = normalize_weights(W)
    assert abs(out[0].sum() - 1.0) < 1e-9
    assert abs(out[1].sum() - 1.0) < 1e-9
    assert out[2].sum() == 0.0
