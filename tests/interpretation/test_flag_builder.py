# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Interpretation flag builder.
"""

from __future__ import annotations

import pytest

from sphere.interpretation.flag_builder import build_interpretation_flags


def test_stable_focus_when_focused_dominant_and_dominant_area_event():
    flags = build_interpretation_flags(
        "focused_dominant",
        ["dominant_area"],
        {},
        {},
    )
    assert "structural_concentration" in flags
    assert "stable_focus" in flags


def test_transition_risk_when_unstable_transition():
    flags = build_interpretation_flags(
        "unstable_transition",
        ["dominance_transition"],
        {},
        {},
    )
    assert "transition_risk" in flags


def test_elevated_tension_when_tension_increase_and_delta_high():
    flags = build_interpretation_flags(
        "tension_elevated",
        ["tension_increase"],
        {},
        {"shadow_diagnostics": {"tension_before": 0.2, "tension_after": 0.35}},
    )
    assert "elevated_tension" in flags
