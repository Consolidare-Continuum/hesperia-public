# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dominant area rule: vector with strong area must trigger rule.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.logic.rule_registry import dominant_area_rule


def test_dominant_area_triggers_when_share_above_threshold():
    area_vector = [0.0] * 12
    area_vector[3] = 0.45
    area_vector[7] = 0.2
    area_vector[0] = 0.35
    state = {"corrected_area_vector": area_vector, "dominant_area_id": 3}
    result = dominant_area_rule(state, None)
    assert result is not None
    assert result["type"] == "dominant_area"
    assert result["area_id"] == 3
    assert result["share"] >= 0.35


def test_dominant_area_no_trigger_when_share_below_threshold():
    area_vector = [0.2, 0.2, 0.2, 0.2, 0.05, 0.05, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0]
    state = {"corrected_area_vector": area_vector, "dominant_area_id": 0}
    result = dominant_area_rule(state, None)
    assert result is None
