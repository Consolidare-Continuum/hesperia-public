# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline execution integration test.
Runs L1→L9 on a short sample sentence via the layer contract; verifies all layers execute and state is populated.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root on path when running tests
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.attribution.structural import (
    attribute,
    load_dict_a,
    load_dict_b,
    normalize,
    tokenize,
)
from core.contracts.layer_contract import LayerInput
from core.layers import build_canonical_stub_adjacency, load_defaults, load_structure_profile
from core.policy import apply_interpretation_policy
from core.stability import run_stability
from sphere.pipeline.layer_registry import LAYERS
from sphere.pipeline.pipeline_state import PipelineState


def test_pipeline_execution_all_nine_layers() -> None:
    """Run pipeline on a short sample sentence; verify all 9 layers executed and state contains 9 layer outputs."""
    text = "justice lie fairness truth good order harm freedom"
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
            policy = apply_interpretation_policy(state, defaults.get("interpretation_policy_mode") or "STRUCTURE_PLUS_CONTEXT")
            input_data.metadata["policy"] = policy
        output = layer_module.run(input_data)
        state.layers[layer_id] = output.result
        state.diagnostics[str(layer_id)] = output.diagnostics

    assert len(state.layers) == 9
    assert "stability" in state.diagnostics, "Pipeline state must contain exactly 9 layer outputs"
    assert "POLICY_MODE" in state.layers[8]
    for lid in range(1, 10):
        assert lid in state.layers, f"Layer {lid} result missing from state.layers"
        assert isinstance(state.layers[lid], dict), f"Layer {lid} result must be a dict"
    for lid in range(1, 10):
        diag = state.diagnostics.get(str(lid), {})
        assert "layer_id" in diag and diag["layer_id"] == lid
        assert "execution_time_ms" in diag, f"Layer {lid} diagnostics must include execution_time_ms"


def test_pipeline_l7_l9_reportable_keys() -> None:
    """After full run, L7 and L9 contain expected reportable keys."""
    text = "justice fairness order"
    assets = _REPO / "assets" / "lexicon" / "curated"
    dict_a = load_dict_a(assets_root=assets) or {}
    dict_b = load_dict_b()
    defaults = load_defaults()
    F = int(defaults.get("F", 288))
    A = int(defaults.get("A", 12))
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
        "MAX_ALLOWED_DEPTH": int(defaults.get("MAX_ALLOWED_DEPTH", 8)),
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
            policy = apply_interpretation_policy(state, "STRUCTURE_PLUS_CONTEXT")
            input_data.metadata["policy"] = policy
        output = layer_module.run(input_data)
        state.layers[layer_id] = output.result
        state.diagnostics[str(layer_id)] = output.diagnostics

    L7 = state.layers[7]
    L9 = state.layers[9]
    assert "DECISION_STATUS_CODE" in L7 and "OUTPUT_TRUST_TAG" in L7
    assert "BRAND_WORD_TRUST" in L9
