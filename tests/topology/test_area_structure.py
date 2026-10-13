# HESPERIA — Tests for LEVEL 1 area structure (TFP domain).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Tests for area_structure_tfp.yaml and load_area_structure_tfp."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_ADJ = _REPO / "assets" / "topology" / "area_adjacency_matrix.json"
_EXPECTED_NEIGHBORS = {
    0: {1, 5, 7, 10, 11},
    1: {0, 5, 7, 8, 9},
    2: {3, 4, 6, 10, 11},
    3: {2, 4, 6, 8, 9},
    4: {2, 3, 5, 9, 11},
    5: {0, 1, 4, 9, 11},
    6: {2, 3, 7, 8, 10},
    7: {0, 1, 6, 8, 10},
    8: {1, 3, 6, 7, 9},
    9: {1, 3, 4, 5, 8},
    10: {0, 2, 6, 7, 11},
    11: {0, 2, 4, 5, 10},
}


def test_load_area_structure_tfp_returns_12_areas() -> None:
    """T1.1: YAML defines exactly 12 areas with area_id A1–A12."""
    from sphere.topology import load_area_structure_tfp
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    data = load_area_structure_tfp(path)
    areas = data["areas"]
    assert data["public_area_count"] == 12
    assert len(areas) == 12
    for i, a in enumerate(areas):
        assert a["area_id"] == f"A{i + 1}"
        assert a["area_index"] == i


def test_a11_a12_locked_names() -> None:
    """TFP-POLES-02: locked RU/EN names for poles."""
    from sphere.topology import load_area_structure_tfp
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    data = load_area_structure_tfp(path)
    by_id = {a["area_id"]: a for a in data["areas"]}
    assert by_id["A11"]["name"] == "Integration / Sublimation"
    assert by_id["A11"]["name_ru"] == "Интеграция / сублимация"
    assert by_id["A12"]["name"] == "Mutual recognition / Anti-grandiosity"
    assert by_id["A12"]["name_ru"] == "Взаимное признание / анти-грандиозность"


def test_area_purpose_fields() -> None:
    """T1.2: Each area has description, clinical_scope, activation_signals, exclusions."""
    from sphere.topology import load_area_structure_tfp
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    data = load_area_structure_tfp(path)
    for a in data["areas"]:
        assert "description" in a
        assert "clinical_scope" in a
        assert "activation_signals" in a
        assert isinstance(a["activation_signals"], list)
        assert "exclusions" in a
        assert isinstance(a["exclusions"], list)


def test_area_neighbors_match_icosahedron() -> None:
    """T1.3: area_neighbors are full-sphere indices 0–11 and match adjacency matrix."""
    from sphere.topology import load_area_structure_tfp
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    data = load_area_structure_tfp(path)
    matrix = json.loads(_ADJ.read_text(encoding="utf-8"))["matrix"]
    for a in data["areas"]:
        neighbors = a["area_neighbors"]
        idx = a["area_index"]
        assert all(0 <= j <= 11 for j in neighbors), f"area {a['area_id']} has invalid neighbor"
        assert set(neighbors) == _EXPECTED_NEIGHBORS[idx]
        assert set(neighbors) == {j for j in range(12) if matrix[idx][j]}


def test_area_distance_matrix_12x12() -> None:
    """T1.3: area_distance_matrix is 12×12, symmetric, zero diagonal, diameter ≤ 3."""
    from sphere.topology import load_area_structure_tfp, get_area_distance_matrix
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    data = load_area_structure_tfp(path)
    matrix = get_area_distance_matrix(path)
    assert len(matrix) == 12
    assert data["public_area_count"] == 12
    for i, row in enumerate(matrix):
        assert len(row) == 12
        assert row[i] == 0
        for j in range(12):
            assert row[j] == matrix[j][i], "matrix must be symmetric"
            assert 0 <= row[j] <= 3, "icosahedron diameter is 3"


def test_get_operational_area_neighbors() -> None:
    """get_operational_area_neighbors returns full-sphere neighbors from YAML."""
    from sphere.topology import get_operational_area_neighbors
    path = _REPO / "spec" / "area_structure_tfp.yaml"
    assert set(get_operational_area_neighbors(0, path=path)) == {1, 5, 7, 10, 11}
    assert set(get_operational_area_neighbors(10, path=path)) == {0, 2, 6, 7, 11}
    assert set(get_operational_area_neighbors(11, path=path)) == {0, 2, 4, 5, 10}
