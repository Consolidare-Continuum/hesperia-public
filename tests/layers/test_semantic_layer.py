# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for semantic layer (L1).
Verifies family hits, dominant family/area, coverage, entropy outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.contracts.layer_contract import LayerInput
from core.layers.layer_1 import compute_L1, run


def test_l1_family_counts_shape() -> None:
    """L1 result includes COVERAGE_RATIO and DOMINANT_FAMILY_ID; hits drive 288 families."""
    F, A = 288, 12
    matched = [(0, 0.5), (1, 0.3)]
    total_tokens = 10
    result = compute_L1(total_tokens, matched, F=F, A=A)
    assert "COVERAGE_RATIO" in result
    assert "DOMINANT_FAMILY_ID" in result
    assert "DOMINANT_AREA_ID" in result
    assert 0 <= result["DOMINANT_FAMILY_ID"] < F
    assert 0 <= result["DOMINANT_AREA_ID"] < A


def test_l1_entropy_bounds() -> None:
    """Normalized family entropy is in [0, 1]."""
    result = compute_L1(100, [(i % 288, 0.5) for i in range(50)], F=288, A=12)
    assert "NORMALIZED_FAMILY_ENTROPY" in result
    assert 0 <= result["NORMALIZED_FAMILY_ENTROPY"] <= 1.0


def test_l1_run_contract() -> None:
    """L1 run() returns LayerOutput with layer_id=1 and result dict."""
    meta = {"F": 288, "A": 12, "eps": 1e-9, "matched": [(0, 0.5)], "hits": [1] + [0] * 287}
    inp = LayerInput(text="test", tokens=["test"], metadata=meta)
    out = run(inp)
    assert out.layer_id == 1
    assert isinstance(out.result, dict)
    assert "DOMINANT_FAMILY_ID" in out.result
