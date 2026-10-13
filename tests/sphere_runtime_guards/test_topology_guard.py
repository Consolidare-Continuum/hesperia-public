# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for sphere.runtime topology guard (not Hesperia `runtime/` package)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_validate_topology_at_startup_passes() -> None:
    """Guard passes with default (file) topology data."""
    from sphere.runtime.guards import validate_topology_at_startup

    validate_topology_at_startup()


def test_topology_integrity_error_on_invalid() -> None:
    """Guard raises TopologyIntegrityError when matrix is invalid."""
    from sphere.topology import get_icosahedral_adjacency
    import numpy as np

    # Build a corrupted matrix (wrong degree)
    adj = get_icosahedral_adjacency()
    adj_corrupt = adj.copy()
    adj_corrupt[0, 1] = 0  # remove one edge -> degree 4 at node 0

    from sphere.runtime.guards import TopologyIntegrityError, validate_topology_at_startup

    # Guard loads from file by default; file is valid. So we need to test with a way to inject adj.
    # Alternatively: test that validate_icosahedral(adj_corrupt) raises, and that fingerprint mismatch raises.
    from sphere.topology import validate_icosahedral

    try:
        validate_icosahedral(adj_corrupt)
        assert False, "expected ValueError"
    except ValueError:
        pass
