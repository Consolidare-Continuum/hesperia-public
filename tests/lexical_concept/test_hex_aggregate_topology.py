# HESPERIA — RAD. Ethan PO-19 / PO-25 helpers.
from __future__ import annotations

from core.hexmap.aggregate import cross_family_relation_sketch
from core.hexmap.analytics import l1_drift, persistence_score
from core.hexmap.topology import neighbor_ring_symbols


def test_cross_family_sketch_sorted() -> None:
    fam = {"F1": 0.5, "F2": 0.25, "F3": 0.1}
    sk = cross_family_relation_sketch(fam, top_k=3)
    assert "top_families" in sk
    assert sk["family_pairs_by_mass_product"]


def test_neighbor_ring_adjacent_indices() -> None:
    mp = {"HX-0": 0, "HX-1": 1, "HX-2": 2}
    ring = neighbor_ring_symbols("HX-1", mp, ring=1)
    assert "HX-1" in ring
    assert "HX-0" in ring and "HX-2" in ring


def test_drift_and_persistence() -> None:
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 0.5, "y": 0.5}
    assert l1_drift(a, b) > 0
    assert 0.0 <= persistence_score(a, b) <= 1.0
