"""H62-008 — D_e hop distance from propagation_trace mock."""
from __future__ import annotations

from core.domain.ksi.hop_distance import hop_distance_from_trace


def test_hop_distance_adjacent_steps() -> None:
    trace = [
        {"concept_id": "a", "step": 0},
        {"concept_id": "b", "step": 1},
        {"concept_id": "c", "step": 2},
    ]
    assert hop_distance_from_trace("a", "c", trace) == 2


def test_hop_distance_empty_trace_defaults_one() -> None:
    assert hop_distance_from_trace("a", "b", None) == 1
