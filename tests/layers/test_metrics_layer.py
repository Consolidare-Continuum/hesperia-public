# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for metrics layer (sphere.metrics).
Verifies entropy, coverage, dominance, tension, loopability bounds and shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_entropy_bounds() -> None:
    """Entropy >= 0; normalized entropy in [0, 1]."""
    from sphere.metrics import compute_entropy, compute_normalized_entropy
    vec = [10.0, 10.0, 10.0, 10.0]
    e = compute_entropy(vec)
    assert e >= 0
    ne = compute_normalized_entropy(vec)
    assert 0 <= ne <= 1.0


def test_entropy_zero_mass() -> None:
    """Zero total mass returns 0 entropy."""
    from sphere.metrics import compute_entropy
    assert compute_entropy([0] * 12) == 0.0


def test_family_coverage_shape() -> None:
    """Family coverage requires 288 counts; returns [0,1]."""
    from sphere.metrics import compute_family_coverage
    import numpy as np
    fc = np.zeros(288)
    fc[0] = 1
    assert compute_family_coverage(fc) == 1 / 288
    assert 0 <= compute_family_coverage(fc) <= 1


def test_dominant_area_and_family() -> None:
    """Dominant area/family are valid indices."""
    from sphere.metrics import detect_dominant_area, detect_dominant_family
    import numpy as np
    av = np.zeros(12)
    av[3] = 0.8
    assert detect_dominant_area(av) == 3
    fc = np.zeros(288)
    fc[100] = 5
    assert detect_dominant_family(fc) == 100


def test_tension_bounds() -> None:
    """Structural tension in [0, 1]."""
    from sphere.metrics import compute_structural_tension
    import numpy as np
    av = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    t = compute_structural_tension(av)
    assert 0 <= t <= 1.0


def test_loopability_bounds() -> None:
    """Loopability in [0, 1]; length-1 sequence gives 0."""
    from sphere.metrics import compute_loopability
    assert compute_loopability([1]) == 0.0
    v = compute_loopability([1, 2, 3, 2, 1])
    assert 0 <= v <= 1.0
