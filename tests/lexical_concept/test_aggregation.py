from __future__ import annotations

from core.hexmap.aggregate import aggregate_hex_state


def test_aggregate_hex_state_rolls_up_to_family_and_area() -> None:
    concept_weights = {"C-1": 1.5, "C-2": 1.0}
    concept_index = {
        "C-1": {"family_ids": ["F1"], "area_ids": ["A1"]},
        "C-2": {"family_ids": ["F1", "F2"], "area_ids": ["A1", "A2"]}
    }
    family, area = aggregate_hex_state(concept_weights, concept_index)
    assert family == {"F1": 2.5, "F2": 1.0}
    assert area == {"A1": 2.5, "A2": 1.0}

