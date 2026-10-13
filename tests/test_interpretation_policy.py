# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Π (Pi) interpretation policy layer tests.
Verify STRUCTURE_ONLY, STRUCTURE_PLUS_CONTEXT, FULL_INTERPRETATION modes and L8 behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.policy.interpretation_policy import (
    STRUCTURE_ONLY,
    STRUCTURE_PLUS_CONTEXT,
    FULL_INTERPRETATION,
    POLICY_MODES,
    apply_interpretation_policy,
)


class _MockState:
    layers = {}
    diagnostics = {}


def test_structure_only_constraints() -> None:
    """STRUCTURE_ONLY: allow_text == False, allow_context == False, allow_structure == True."""
    state = _MockState()
    policy = apply_interpretation_policy(state, STRUCTURE_ONLY)
    assert policy["policy_mode"] == STRUCTURE_ONLY
    c = policy["interpretation_constraints"]
    assert c["allow_text"] is False
    assert c["allow_context"] is False
    assert c["allow_structure"] is True
    assert "allowed_fields" in policy and "forbidden_fields" in policy


def test_structure_plus_context_constraints() -> None:
    """STRUCTURE_PLUS_CONTEXT: allow_text == True, allow_context == True, allow_structure == True."""
    state = _MockState()
    policy = apply_interpretation_policy(state, STRUCTURE_PLUS_CONTEXT)
    assert policy["policy_mode"] == STRUCTURE_PLUS_CONTEXT
    c = policy["interpretation_constraints"]
    assert c["allow_text"] is True
    assert c["allow_context"] is True
    assert c["allow_structure"] is True


def test_full_interpretation_no_restrictions() -> None:
    """FULL_INTERPRETATION: no restrictions (all True)."""
    state = _MockState()
    policy = apply_interpretation_policy(state, FULL_INTERPRETATION)
    assert policy["policy_mode"] == FULL_INTERPRETATION
    c = policy["interpretation_constraints"]
    assert c["allow_text"] is True
    assert c["allow_context"] is True
    assert c["allow_structure"] is True


def test_policy_structure() -> None:
    """Policy has required keys."""
    state = _MockState()
    for mode in POLICY_MODES:
        policy = apply_interpretation_policy(state, mode)
        assert "policy_mode" in policy
        assert "allowed_fields" in policy
        assert "forbidden_fields" in policy
        assert "interpretation_constraints" in policy
        assert "allow_text" in policy["interpretation_constraints"]
        assert "allow_context" in policy["interpretation_constraints"]
        assert "allow_structure" in policy["interpretation_constraints"]


def test_l8_receives_policy_and_sets_scope() -> None:
    """Pipeline run: policy applied before L8, L8 result contains POLICY_MODE and INTERPRETATION_SCOPE."""
    from core.attribution.structural import (
        attribute,
        load_dict_a,
        load_dict_b,
        normalize,
        tokenize,
    )
    from core.contracts.layer_contract import LayerInput
    from core.layers import build_canonical_stub_adjacency, load_defaults
    from core.policy import apply_interpretation_policy
    from core.stability import run_stability
    from sphere.pipeline.layer_registry import LAYERS
    from sphere.pipeline.pipeline_state import PipelineState

    text = "Justice and order."
    assets = _REPO / "assets" / "lexicon" / "curated"
    dict_a = load_dict_a(assets_root=assets) or {}
    dict_b = load_dict_b()
    defaults = load_defaults()
    F = int(defaults.get("F", 288))
    A = int(defaults.get("A", 12))
    D = int(defaults.get("MAX_ALLOWED_DEPTH", 8))
    tokens = tokenize(normalize(text))
    matched, _ = attribute(tokens, dict_a, dict_b)
    hits = [0] * F
    for fg, _ in matched:
        if 0 <= fg < F:
            hits[fg] += 1
    adjacency = build_canonical_stub_adjacency(F, A)
    state = PipelineState()
    metadata = {
        "F": F,
        "A": A,
        "eps": float(defaults.get("eps", 1e-9)),
        "defaults": defaults,
        "matched": matched,
        "hits": hits,
        "adjacency": adjacency,
        "profile_id": None,
        "profile": None,
        "MAX_ALLOWED_DEPTH": D,
    }
    input_data = LayerInput(text=text, tokens=tokens, metadata=metadata)

    for layer_id, layer_module in LAYERS:
        input_data.metadata["layers"] = dict(state.layers)
        if layer_id >= 2 and 2 in state.layers:
            input_data.metadata["visited_B"] = set(state.layers[2].get("VISITED_IDS", []))
        if layer_id == 7:
            stability_out = run_stability(state.layers)
            state.diagnostics["stability"] = stability_out
            input_data.metadata["stability"] = stability_out
        if layer_id == 8:
            policy = apply_interpretation_policy(state, STRUCTURE_ONLY)
            input_data.metadata["policy"] = policy
        output = layer_module.run(input_data)
        state.layers[layer_id] = output.result
        state.diagnostics[str(layer_id)] = output.diagnostics

    L8 = state.layers[8]
    assert "POLICY_MODE" in L8
    assert L8["POLICY_MODE"] == STRUCTURE_ONLY
    assert "INTERPRETATION_CONSTRAINTS" in L8
    assert L8["INTERPRETATION_CONSTRAINTS"]["allow_text"] is False
    assert "INTERPRETATION_SCOPE" in L8
    assert L8["INTERPRETATION_SCOPE"] == "structure_only"
