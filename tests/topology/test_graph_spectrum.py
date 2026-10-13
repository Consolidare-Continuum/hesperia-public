# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Spectral sanity tests for icosahedral adjacency matrix.
Verifies 5-regular structure via maximum eigenvalue.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_degree_regular() -> None:
    """Maximum eigenvalue of adjacency matrix equals 5 (5-regular graph)."""
    from sphere.topology import load_area_adjacency, ICOSAHEDRAL_DEGREE

    A = load_area_adjacency()
    eigvals = np.linalg.eigvals(A.astype(np.float64))
    max_real = float(max(eigvals).real)
    assert round(max_real) == ICOSAHEDRAL_DEGREE, (
        f"5-regular graph must have max eigenvalue 5, got {max_real}"
    )
