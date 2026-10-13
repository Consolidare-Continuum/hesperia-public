# GTP-05 — legal neighbors N(h) + GTPA next-hex selection.

from __future__ import annotations

import pytest

from sphere.topology.gtp.coherence import compute_coherence_field
from sphere.topology.gtp.gtpa import gtpa_next_hex
from sphere.topology.gtp.ipow import POINT_ZERO, point_zero_delta
from sphere.topology.gtp.neighbors import HexCell, legal_neighbors
from sphere.topology.gtp.rotation import input_features


def test_hex_cell_validates_global_id_area_consistency() -> None:
    with pytest.raises(ValueError):
        HexCell(area_id=0, global_id=100, hex_index=0)  # global_id belongs to area 4


def test_hex_cell_rejects_out_of_range_hex_index() -> None:
    with pytest.raises(ValueError):
        HexCell(area_id=0, global_id=0, hex_index=250)


def test_legal_neighbors_count_is_nine() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    neighbors = legal_neighbors(h)
    # 5 area-ring (icosahedral degree 5) + 2 family-patch + 2 hex-index
    assert len(neighbors) == 9


def test_legal_neighbors_family_and_hex_steps_stay_in_area() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    neighbors = legal_neighbors(h)
    same_area = [n for n in neighbors if n.area_id == h.area_id]
    # 2 family-patch + 2 hex-index neighbors keep area_id fixed
    assert len(same_area) == 4


def test_legal_neighbors_hex_index_wraps_mod_250() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=0)
    neighbors = legal_neighbors(h)
    hex_indices = {n.hex_index for n in neighbors if n.area_id == h.area_id and n.global_id == h.global_id}
    assert hex_indices == {249, 1}


def test_gtpa_next_hex_is_deterministic() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    phi = input_features("this includes and overlaps partially with something")
    psi = compute_coherence_field(point_zero_delta((0.3, -0.2, 0.15)))
    r1 = gtpa_next_hex(h, psi=psi, phi=phi, hex_rotation=0)
    r2 = gtpa_next_hex(h, psi=psi, phi=phi, hex_rotation=0)
    assert r1 == r2
    assert r1.next_hex in legal_neighbors(h)


def test_gtpa_next_hex_at_point_zero_uniform_psi_falls_back_to_deterministic_tiebreak() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    phi = input_features("no operator keywords here at all")
    psi = compute_coherence_field(point_zero_delta(POINT_ZERO))
    result = gtpa_next_hex(h, psi=psi, phi=phi, hex_rotation=0)
    # With zero coherence and no side matches, PathPrior is uniform (1.0) for all —
    # tie-break must pick lowest (global_id, hex_index) among the 9 legal neighbors.
    candidates = sorted(legal_neighbors(h), key=lambda c: (c.global_id, c.hex_index))
    assert result.next_hex == candidates[0]
