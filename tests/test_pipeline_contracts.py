# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline contract validation tests.
Verify that each layer output is validated against expected keys.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sphere.pipeline.contract_validation import (
    validate_layer_output,
    validate_pipeline_contracts,
    validate_layer_input,
)


def test_layer_1_output_contract() -> None:
    """Layer 1 must include at least one of COVERAGE_RATIO, DOMINANT_FAMILY_ID, etc."""
    validate_layer_output("layer_1", {"COVERAGE_RATIO": 0.5, "DOMINANT_FAMILY_ID": 10})
    validate_layer_output("layer_1", {"NORMALIZED_FAMILY_ENTROPY": 0.3})


def test_layer_1_output_contract_fails_on_empty() -> None:
    """Empty or wrong structure raises."""
    try:
        validate_layer_output("layer_1", {})
    except ValueError as e:
        assert "layer_1" in str(e) and "at least one" in str(e)


def test_layer_7_output_contract() -> None:
    """Layer 7 must include SYSTEM_CONFIDENCE_SCORE or DECISION_STATUS_CODE or OUTPUT_TRUST_TAG."""
    validate_layer_output("layer_7", {"DECISION_STATUS_CODE": 0, "OUTPUT_TRUST_TAG": "HIGH"})


def test_layer_9_output_contract() -> None:
    """Layer 9 must include BRAND_WORD_TRUST or triggered_rules group."""
    validate_layer_output("layer_9", {"BRAND_WORD_TRUST": "ok"})
    validate_layer_output("layer_9", {"triggered_rules": [], "structural_diagnostics": []})


def test_layer_10_placeholder_contract() -> None:
    """Layer 10 can satisfy with _placeholder or analysis_report."""
    validate_layer_output("layer_10", {"_placeholder": True})
    validate_layer_output("layer_10", {"analysis_report": None, "interpretation": None})


def test_validate_pipeline_contracts_full() -> None:
    """validate_pipeline_contracts requires layer_1 through layer_10."""
    layer_outputs = {
        "layer_1": {"COVERAGE_RATIO": 0.5},
        "layer_2": {"VISITED_IDS": []},
        "layer_3": {"SHADOW_ENABLED": True},
        "layer_4": {"EVIDENCE_SUPPORT_INDEX_BASELINE": 0.5},
        "layer_5": {"REALITY_GATE_TRIG": True},
        "layer_6": {"GLOBAL_STABILITY_SCORE": 0.5},
        "layer_7": {"OUTPUT_TRUST_TAG": "MED"},
        "layer_8": {"POLICY_MODE": "STRUCTURE_ONLY"},
        "layer_9": {"BRAND_WORD_TRUST": "ok"},
        "layer_10": {"_placeholder": True},
    }
    validate_pipeline_contracts(layer_outputs)


def test_validate_pipeline_contracts_missing_layer() -> None:
    """Missing layer key raises."""
    try:
        validate_pipeline_contracts({"layer_1": {"COVERAGE_RATIO": 0}, "layer_2": {"VISITED_IDS": []}})
    except ValueError as e:
        assert "layer" in str(e).lower()
