# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dominance transition rule: two sequential states detect change.
Propagation spread rule: large diffusion triggers event.
"""

from __future__ import annotations

import pytest

from sphere.logic.rule_registry import dominance_transition_rule, propagation_spread_rule


def test_dominance_transition_triggers_when_dominant_changes():
    state = {"dominant_area_id": 5}
    previous = {"dominant_area_id": 2}
    result = dominance_transition_rule(state, previous)
    assert result is not None
    assert result["type"] == "dominance_transition"
    assert result["from"] == 2
    assert result["to"] == 5


def test_dominance_transition_no_trigger_when_same():
    state = {"dominant_area_id": 3}
    previous = {"dominant_area_id": 3}
    result = dominance_transition_rule(state, previous)
    assert result is None


def test_dominance_transition_no_trigger_without_previous():
    state = {"dominant_area_id": 3}
    result = dominance_transition_rule(state, None)
    assert result is None


def test_propagation_spread_triggers_when_many_areas_affected():
    state = {"propagation_diagnostics": {"active_edges_count": 24}}
    result = propagation_spread_rule(state, None)
    assert result is not None
    assert result["type"] == "propagation_spread"
    assert result["areas_affected"] >= 2

