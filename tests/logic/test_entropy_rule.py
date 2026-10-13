# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Entropy drop rule: large entropy reduction must trigger event.
"""

from __future__ import annotations

import pytest

from sphere.logic.rule_registry import entropy_drop_rule


def test_entropy_drop_triggers_when_delta_above_threshold():
    state = {
        "corrected_area_vector": [0.5, 0.5] + [0.0] * 10,
        "shadow_diagnostics": {"entropy_before": 3.0, "entropy_after": 2.7},
    }
    result = entropy_drop_rule(state, None)
    assert result is not None  # 0.3 drop >= 0.15
    assert result["type"] == "entropy_drop"
    assert result["delta_entropy"] >= 0.15


def test_entropy_drop_no_trigger_when_delta_small():
    state = {
        "shadow_diagnostics": {"entropy_before": 2.0, "entropy_after": 1.9},
    }
    result = entropy_drop_rule(state, None)
    assert result is None
