from __future__ import annotations

from core.hexmap.dynamics import apply_decay, concentration_index, dispersion_index
from core.hexmap.projection import project_concepts_to_hex


def test_projection_returns_degradation_for_missing_anchor() -> None:
    state, flags = project_concepts_to_hex({"C-1": 1.0, "C-2": 2.0}, {"C-1": "HX-1"})
    assert state == {"HX-1": 1.0}
    assert flags == ["missing_anchor:C-2"]


def test_hex_dynamics_indexes_are_deterministic() -> None:
    hex_state = {"HX-1": 2.0, "HX-2": 1.0}
    decayed = apply_decay(hex_state, decay=0.1)
    assert decayed == {"HX-1": 1.8, "HX-2": 0.9}
    assert concentration_index(decayed) == 1.8 / 2.7
    assert dispersion_index(decayed) == 1.0

