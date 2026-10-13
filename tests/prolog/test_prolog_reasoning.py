# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog L9b: rule chaining and derived facts.
"""

from __future__ import annotations

import pytest

from sphere.prolog_logic.engine import compute_prolog_inference


def _logic_metrics(triggered_types: list[str]):
    return {
        "triggered_rules": [{"type": t} for t in triggered_types],
        "dominance_events": [],
        "entropy_events": [],
        "tension_events": [],
        "anomaly_flags": [],
        "logic_diagnostics": {},
    }


def _interpretation_metrics(active_events: list[str], structural_state: str = "focused_dominant"):
    return {
        "structural_state": structural_state,
        "dominant_area_id": 0,
        "dominance_strength": 0.4,
        "entropy_state": "reduced_after_shadow",
        "tension_state": "normal",
        "propagation_state": "minimal_spread",
        "active_events": active_events,
        "interpretation_flags": [],
        "event_summary": {},
        "interpretation_diagnostics": {},
    }


def test_structural_focus_derived_from_dominant_area_and_entropy_drop():
    """dominant_area + entropy_drop -> structural_focus via default rules."""
    logic = _logic_metrics(["dominant_area", "entropy_drop"])
    interp = _interpretation_metrics(["dominant_area", "entropy_drop"])
    out = compute_prolog_inference(logic, interp, None)
    derived = out.get("derived_facts", [])
    preds = [d["predicate"] for d in derived]
    assert "structural_focus" in preds
    assert "derived_facts" in out
    assert "rule_traces" in out
    assert "prolog_diagnostics" in out


def test_transition_risk_derived_from_dominance_transition():
    """dominance_transition -> transition_risk."""
    logic = _logic_metrics(["dominance_transition"])
    interp = _interpretation_metrics(["dominance_transition"], structural_state="unstable_transition")
    out = compute_prolog_inference(logic, interp, None)
    preds = [d["predicate"] for d in out.get("derived_facts", [])]
    assert "transition_risk" in preds


def test_no_derived_facts_when_preconditions_missing():
    """Only entropy_drop (no dominant_area) does not derive structural_focus."""
    logic = _logic_metrics(["entropy_drop"])
    interp = _interpretation_metrics(["entropy_drop"])
    out = compute_prolog_inference(logic, interp, None)
    preds = [d["predicate"] for d in out.get("derived_facts", [])]
    assert "structural_focus" not in preds


def test_prolog_output_structure():
    """Result has derived_facts, rule_traces, prolog_diagnostics."""
    out = compute_prolog_inference(
        _logic_metrics([]),
        _interpretation_metrics([]),
        None,
    )
    assert isinstance(out["derived_facts"], list)
    assert isinstance(out["rule_traces"], list)
    assert isinstance(out["prolog_diagnostics"], dict)
    assert "iterations" in out["prolog_diagnostics"]
    assert "facts_initial" in out["prolog_diagnostics"]
    assert "facts_final" in out["prolog_diagnostics"]
    assert "rules_fired" in out["prolog_diagnostics"]


def test_rule_trace_frozen_schema():
    """Rule trace entries: set(trace.keys()) == {"rule", "premises", "derived", "iteration"}."""
    from sphere.prolog_logic.engine import TRACE_KEYS

    logic = _logic_metrics(["dominance_transition"])
    interp = _interpretation_metrics(["dominance_transition"])
    out = compute_prolog_inference(logic, interp, None)
    traces = out.get("rule_traces", [])
    assert len(traces) >= 1
    for t in traces:
        assert set(t.keys()) == TRACE_KEYS, f"trace keys must be exactly {TRACE_KEYS}, got {set(t.keys())}"
        assert t["rule"].endswith("_rule")
        assert isinstance(t["premises"], list)
        assert isinstance(t["derived"], str)
        assert isinstance(t["iteration"], int)
        assert t["iteration"] >= 1


def test_pipeline_prolog_disabled_keeps_prolog_logic_empty():
    """When enable_prolog is False, result contains prolog_logic with empty or minimal structure."""
    from sphere.pipeline import run_pipeline
    config = {"pipeline_version": "v1", "deterministic": True}
    result = run_pipeline("short text", config, document_id="noprolog")
    assert "prolog_logic" in result
    assert "derived_facts" in result["prolog_logic"]
    assert "prolog_diagnostics" in result["prolog_logic"]
    assert result["prolog_logic"].get("derived_facts") == []


def test_pipeline_prolog_enabled_populates_prolog_logic():
    """When enable_prolog is True, Prolog runs and result contains prolog_logic with diagnostics."""
    from sphere.pipeline import run_pipeline
    config = {"pipeline_version": "v1", "deterministic": True, "enable_prolog": True}
    result = run_pipeline("justice order fairness truth", config, document_id="prolog_on")
    assert "prolog_logic" in result
    assert "derived_facts" in result["prolog_logic"]
    assert "rule_traces" in result["prolog_logic"]
    assert "prolog_diagnostics" in result["prolog_logic"]
    assert "iterations" in result["prolog_logic"]["prolog_diagnostics"]
