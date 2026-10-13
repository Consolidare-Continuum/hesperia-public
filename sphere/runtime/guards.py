# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Runtime topology guard: validate icosahedral invariants and fingerprint at startup.
Prevents silent corruption by failing fast if topology data is invalid or mismatched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class TopologyIntegrityError(RuntimeError):
    """Raised when topology validation or fingerprint check fails at startup."""

    pass


# Expected fingerprint of the canonical icosahedral adjacency (computed once at import).
def _expected_fingerprint() -> str:
    from sphere.topology import get_icosahedral_adjacency, topology_fingerprint
    return topology_fingerprint(get_icosahedral_adjacency())


EXPECTED_TOPOLOGY_FINGERPRINT = _expected_fingerprint()


def validate_topology_at_startup(data_root: Optional[Path] = None) -> None:
    """
    Run topology integrity checks: validate_icosahedral() and fingerprint match.
    Call at runtime startup. Raises TopologyIntegrityError on failure.
    """
    from sphere.topology import load_area_adjacency, validate_icosahedral, topology_fingerprint

    try:
        adj = load_area_adjacency(data_root)
    except Exception as e:
        raise TopologyIntegrityError(f"Failed to load area adjacency: {e}") from e

    try:
        validate_icosahedral(adj)
    except ValueError as e:
        raise TopologyIntegrityError(f"Topology validation failed: {e}") from e

    fp = topology_fingerprint(adj)
    if fp != EXPECTED_TOPOLOGY_FINGERPRINT:
        raise TopologyIntegrityError(
            f"Topology fingerprint mismatch: expected {EXPECTED_TOPOLOGY_FINGERPRINT}, got {fp}. "
            "Topology data may be corrupted or modified."
        )
