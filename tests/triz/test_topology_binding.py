# Topology binding & area metrics

from __future__ import annotations

from hesperia.extensions.triz.models import ContradictionSignal, MatrixCoordinate
from hesperia.extensions.triz.topology_binding import bind_concept_to_matrix, bind_contradiction_to_topology
from hesperia.extensions.triz.topology_metrics import area_distance, canonical_area_adjacency, contradiction_locality_score


def test_bind_concept_read_only() -> None:
    m = {"c": {"area_id": 3, "family_id": 8, "hex_id": 203}}
    r = bind_concept_to_matrix("c", m)
    assert r.area_id == 3 and r.family_id == 8 and r.hex_id == 203
    assert bind_concept_to_matrix("missing", m).area_id == -1


def test_bind_contradiction_adjacency() -> None:
    c = ContradictionSignal(
        "a",
        "b",
        0.5,
        "parameter_change",
        MatrixCoordinate(0, 1, None),
        MatrixCoordinate(0, 2, None),
    )
    mapping = {
        "a": {"area_id": 0, "family_id": 1, "hex_id": None},
        "b": {"area_id": 0, "family_id": 2, "hex_id": None},
    }
    b = bind_contradiction_to_topology(c, mapping)
    assert b["same_area"] is True
    assert b["adjacent_areas"] is False


def test_area_distance_symmetric_and_locality() -> None:
    adj = canonical_area_adjacency()
    assert len(adj) == 12 and len(adj[0]) == 12
    n0 = [j for j in range(12) if adj[0][j] == 1]
    assert len(n0) == 5
    for nb in n0:
        assert area_distance(0, nb) == 1
    assert area_distance(0, 0) == 0
    loc = contradiction_locality_score(0, n0[0])
    assert loc == round(1.0 / 2.0, 6)
