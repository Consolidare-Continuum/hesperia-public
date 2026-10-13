# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
TFP-POLES-01 gate: full A1-A12 outcome surfaces + pole_cascade audit block.

Contract: colombo_research/hesperia/COLOMBO-POLES-OUTCOMES-CHAIN-2026-08-21.md
(operator-ratified 2026-08-21; Grace triage
GRACE-TRIAGE-TFP-POLES-OUTCOME-SCHEMA-2026-08-21.md, row TFP-POLES-01).

Covers: RU name lock, area_ids/inhibition-matrix 12-key shape, dominant-area
selection landing on a pole, and the pole_cascade seed/hop-1/hop-2/tension
arithmetic — not the Dict-B mass fill (separate, later wave).
"""

from __future__ import annotations

from research.clinical_tfp.interpretation import get_dominant_area
from research.clinical_tfp.pole_cascade import (
    POLE_AREAS,
    TENSION_LEGS,
    _hop_sets,
    build_pole_cascade,
)
from research.clinical_tfp.report_generator import AREA_NAMES_RU
from hesperia.engine.tfp_signal_calibration import get_area_ids, load_area_inhibition_matrix

LOCKED_RU = {
    "A11": "интеграция / сублимация",
    "A12": "взаимное признание / анти-грандиозность",
}


def test_area_names_ru_locked_poles():
    for area_id, name in LOCKED_RU.items():
        assert AREA_NAMES_RU.get(area_id) == name


def test_area_names_ru_covers_all_twelve():
    assert set(AREA_NAMES_RU.keys()) == {f"A{i}" for i in range(1, 13)}


def test_area_ids_are_full_twelve():
    area_ids = get_area_ids()
    assert len(area_ids) == 12
    assert set(POLE_AREAS) <= set(area_ids)


def test_inhibition_matrix_shape_is_twelve_by_twelve():
    payload = load_area_inhibition_matrix()
    assert payload["area_ids"] == get_area_ids()
    matrix = payload["matrix"]
    assert len(matrix) == 12
    assert all(len(row) == 12 for row in matrix)


def test_dominant_area_can_land_on_a_pole():
    scores = {"A1": 0.1, "A3": 0.2, "A11": 0.9, "A12": 0.4}
    assert get_dominant_area(scores) == "A11"


def test_pole_cascade_hop_sets_match_locked_contract():
    hop1, hop2 = _hop_sets()
    assert hop1 == frozenset({"A1", "A3", "A5", "A6", "A7", "A8"})
    assert hop2 == frozenset({"A2", "A4", "A9", "A10"})
    # every area is reachable within 2 hops (topology fact, not "border all at hop-1")
    assert hop1 | hop2 | set(POLE_AREAS) == {f"A{i}" for i in range(1, 13)}


def test_pole_cascade_seed_hop_and_tension_arithmetic():
    areas_raw = {"A11": 0.4, "A12": 0.3, "A5": 0.2, "A6": 0.1, "A1": 0.05}
    areas_inhibited = {"A11": 0.35, "A12": 0.28, "A5": 0.18, "A6": 0.05, "A1": 0.04}

    out = build_pole_cascade(areas_raw, areas_inhibited)

    assert out["poles"] == list(POLE_AREAS)
    assert out["seed"]["raw"] == {"A11": 0.4, "A12": 0.3}
    assert out["seed"]["inhibited"] == {"A11": 0.35, "A12": 0.28}

    assert set(out["hop1_delta"].keys()) == {"A1", "A3", "A5", "A6", "A7", "A8"}
    assert out["hop1_delta"]["A1"] == areas_inhibited["A1"] - areas_raw["A1"]
    assert out["hop1_delta"]["A5"] == areas_inhibited["A5"] - areas_raw["A5"]
    assert out["hop1_delta"]["A3"] == 0.0  # missing from both inputs -> 0.0 - 0.0

    assert set(out["hop2_delta"].keys()) == {"A2", "A4", "A9", "A10"}
    assert all(v == 0.0 for v in out["hop2_delta"].values())

    for a, b in TENSION_LEGS:
        leg = out["tension"][f"{a}_{b}"]
        assert leg["raw"] == abs(areas_raw.get(a, 0.0) - areas_raw.get(b, 0.0))
        assert leg["inhibited"] == abs(areas_inhibited.get(a, 0.0) - areas_inhibited.get(b, 0.0))


def test_pole_cascade_defaults_safe_on_missing_areas():
    out = build_pole_cascade(None, None)
    assert out["seed"]["raw"] == {"A11": 0.0, "A12": 0.0}
    assert all(v == 0.0 for v in out["hop1_delta"].values())
    assert all(v == 0.0 for v in out["hop2_delta"].values())
