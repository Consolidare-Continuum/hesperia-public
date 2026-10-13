# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for shadow / L3 divergence and L8 policy layer.
Verifies shadow-related outputs and L8 contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.contracts.layer_contract import LayerInput
from core.layers.layer_8 import run


def test_l8_output_contract() -> None:
    """L8 result includes POLICY_MODE and INTERPRETATION_SCOPE."""
    meta = {
        "layers": {
            1: {"TOTAL_TOKENS": 10, "COVERAGE_RATIO": 0.5, "DOMINANCE_RATIO": 0.3, "NORMALIZED_FAMILY_ENTROPY": 0.4},
            2: {"GEOMETRIC_STABILITY_INDEX": 0.8, "CROSS_AREA_RATIO": 0.1},
            3: {"SHADOW_DEVIATION_SCORE": 0.0},
            4: {"EVIDENCE_SUPPORT_INDEX_BASELINE": 0.7},
            5: {"CONTRADICTION_PRESSURE_SCORE": 0.2, "REALITY_GATE_TRIG": True},
            6: {"GLOBAL_STABILITY_SCORE": 0.9},
            7: {"SYSTEM_CONFIDENCE_SCORE": 0.85},
        },
        "policy": {"policy_mode": "STRUCTURE_ONLY", "interpretation_constraints": {}},
    }
    inp = LayerInput(text="test", tokens=["test"], metadata=meta)
    out = run(inp)
    assert out.layer_id == 8
    assert "POLICY_MODE" in out.result
    assert "INTERPRETATION_SCOPE" in out.result
