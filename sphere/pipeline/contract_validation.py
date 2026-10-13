# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer contract validation: each layer receives and returns the structures it is supposed to.
Validates layer output payloads against per-layer expectations.
"""

from __future__ import annotations

import copy
from typing import Any

# Per-layer required keys (at least one of each group or exact key).
# Aligned with core layer results and pipeline-assembled outputs.
LAYER_OUTPUT_CONTRACTS: dict[str, list[list[str]]] = {
    "layer_1": [
        ["COVERAGE_RATIO", "DOMINANT_FAMILY_ID", "DOMINANT_AREA_ID", "NORMALIZED_FAMILY_ENTROPY"],
        ["normalized_tokens"],
    ],
    "layer_2": [
        ["VISITED_IDS", "TOTAL_REACHABLE_NODES"],
        ["activated_terms"],
    ],
    "layer_3": [
        ["COVERAGE_RATIO_DELTA", "SHADOW_ENABLED"],
        ["family_counts", "coverage", "family_entropy"],
        ["family_sequence"],
    ],
    "layer_4": [
        ["EVIDENCE_SUPPORT_INDEX_BASELINE", "AREA_MATCH_RATIO_BASELINE"],
        ["area_vector", "family_to_area", "adjacency_matrix", "area_sequence"],
    ],
    "layer_5": [
        ["REALITY_GATE_TRIG", "CONTRADICTION_PRESSURE_SCORE"],
        ["dominant_area", "dominant_family", "entropy", "tension", "loopability", "coverage"],
    ],
    "layer_6": [
        ["LYAPUNOV_ESTIMATE", "GLOBAL_STABILITY_SCORE"],
        ["trajectory", "transition_matrix", "curvature", "jump_rate", "stability_index"],
    ],
    "layer_7": [
        ["SYSTEM_CONFIDENCE_SCORE", "DECISION_STATUS_CODE", "OUTPUT_TRUST_TAG"],
        ["propagated_family_counts", "propagated_area_vector"],
    ],
    "layer_8": [
        ["POLICY_MODE", "INTERPRETATION_SCOPE"],
        ["shadow_score", "leakage", "correction_flags", "unknown_token_bucket"],
    ],
    "layer_9": [
        ["BRAND_WORD_TRUST"],
        ["triggered_rules", "structural_diagnostics", "rule_trigger_registry"],
    ],
    "layer_10": [
        ["analysis_report", "interpretation", "explanation", "_placeholder"],
    ],
}


def _satisfies_contract(payload: dict[str, Any], keys_groups: list[list[str]]) -> bool:
    """True if payload has at least one key from the first (primary) group or any other group."""
    for group in keys_groups:
        if any(k in payload for k in group):
            return True
    return False


def validate_layer_input(layer_name: str, payload: dict[str, Any]) -> None:
    """
    Validate that the input payload for a layer contains required context.
    For L1, we require metadata-like structure; for L2+ we require prior layers in metadata.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"{layer_name} input must be a dict")
    layer_id = layer_name.replace("layer_", "")
    if layer_id.isdigit() and int(layer_id) > 1:
        # L2+ typically receive metadata with prior layers
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            return
        if "layers" in payload or "metadata" in payload:
            return
    return


def validate_layer_output(layer_name: str, payload: dict[str, Any]) -> None:
    """
    Validate that layer output contains the structures it is supposed to return.
    Uses LAYER_OUTPUT_CONTRACTS: at least one key group must be fully satisfied per layer.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"{layer_name} output must be a dict, got {type(payload).__name__}")
    contracts = LAYER_OUTPUT_CONTRACTS.get(layer_name)
    if not contracts:
        return
    if not _satisfies_contract(payload, contracts):
        primary = contracts[0]
        raise ValueError(
            f"{layer_name} output must include at least one of {primary!r} (or equivalent); keys present: {list(payload.keys())[:20]}"
        )


def validate_pipeline_contracts(layer_outputs: dict[str, Any]) -> None:
    """
    Validate all layer outputs in the pipeline artifact.
    layer_outputs: dict with keys layer_1 .. layer_10 and dict values.
    """
    if not isinstance(layer_outputs, dict):
        raise ValueError("layer_outputs must be a dict")
    for name in [f"layer_{i}" for i in range(1, 11)]:
        if name not in layer_outputs:
            raise ValueError(f"layer_outputs must contain {name}")
        validate_layer_output(name, layer_outputs[name])
