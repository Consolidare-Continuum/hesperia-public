# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
State classifier: structural_state, entropy_state, tension_state, propagation_state.
"""

from __future__ import annotations

import pytest

from sphere.interpretation.state_classifier import (
    classify_structural_state,
    classify_entropy_state,
    classify_tension_state,
    classify_propagation_state,
)


def test_entropy_state_reduced_after_shadow():
    diag = {"entropy_before": 3.0, "entropy_after": 2.7}
    assert classify_entropy_state(diag) == "reduced_after_shadow"


def test_entropy_state_stable():
    diag = {"entropy_before": 2.0, "entropy_after": 2.02}
    assert classify_entropy_state(diag) == "stable"


def test_tension_state_elevated():
    diag = {"tension_before": 0.2, "tension_after": 0.35}
    assert classify_tension_state(diag) == "elevated"


def test_tension_state_normal():
    diag = {"tension_before": 0.5, "tension_after": 0.52}
    assert classify_tension_state(diag) == "normal"


def test_propagation_state_moderate():
    diag = {"active_edges_count": 5}
    assert classify_propagation_state(diag) == "moderate_spread"


def test_propagation_state_minimal():
    diag = {"active_edges_count": 0}
    assert classify_propagation_state(diag) == "minimal_spread"


def test_structural_state_unstable_transition():
    logic = {"triggered_rules": [{"type": "dominance_transition"}], "logic_diagnostics": {}}
    shadow = {"corrected_area_vector": [0.5] + [0.05] * 11, "shadow_diagnostics": {"entropy_after": 2.0}}
    state, reason = classify_structural_state(logic, shadow)
    assert state == "unstable_transition"
    assert "dominance_transition" in reason
