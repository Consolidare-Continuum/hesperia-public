# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for topology layer (L4 book evidence + sphere topology).
Verifies area match, evidence support, and topology loader outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_topology_loader_area_adjacency_shape() -> None:
    """Loaded area adjacency matrix is 12x12."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    assert matrix.shape == (12, 12)


def test_topology_loader_family_mapping_length() -> None:
    """Family to area mapping has 288 entries."""
    from sphere.topology import load_family_area_mapping
    mapping = load_family_area_mapping()
    assert len(mapping) == 288
    assert all(0 <= int(a) < 12 for a in mapping)


def test_topology_graph_neighbors() -> None:
    """Topology graph has neighbors dict for 12 areas."""
    from sphere.topology import build_topology_graph
    graph = build_topology_graph()
    assert graph["areas"] == 12
    assert "neighbors" in graph
    for i in range(12):
        assert i in graph["neighbors"]
        assert isinstance(graph["neighbors"][i], list)
