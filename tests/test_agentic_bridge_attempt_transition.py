"""Gold test for fpf_bridge_v7_3 Phase B: attempt_hesperia_transition.

Spec: specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md §1.2, §8.

Honest scope note (see module docstring in attempt_transition.py): the installed
fpf-thinking-map version's GatePrimitive.evaluate() never produces GateDecision.BLOCK — only
ABSTAIN/DEGRADE/PASS. So the real, observable enforcement outcomes today are ABSTAIN (unknown
transition, wrong state, or a gate that can't pass) and COLLECT_EVIDENCE (evidence gap) — not a
literal "BLOCK" kind. These tests prove those real outcomes rather than a BLOCK case the library
cannot currently produce.
"""
from __future__ import annotations

import pytest

from runtime.agentic_bridge.attempt_transition import (
    BridgeActDisabledError,
    attempt_hesperia_transition,
)
from tests.fixtures.mock_pipeline_result import make_pipeline_result


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HESPERIA_MCP_BRIDGE_ACT_ENABLED", raising=False)
    result = make_pipeline_result()
    with pytest.raises(BridgeActDisabledError):
        attempt_hesperia_transition(result, branch="tfp", transition_id="focused_to_distributed")


def test_branch_validated(monkeypatch):
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ACT_ENABLED", "1")
    result = make_pipeline_result()
    with pytest.raises(ValueError):
        attempt_hesperia_transition(result, branch="mrt", transition_id="focused_to_distributed")  # type: ignore[arg-type]


def test_missing_evidence_yields_collect_evidence_outcome(monkeypatch):
    """focused_to_unstable requires rule_dominance_transition evidence the default fixture
    doesn't produce — this must come back as a real, actionable gap, not a silent pass."""
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ACT_ENABLED", "1")
    result = make_pipeline_result()
    outcome = attempt_hesperia_transition(
        result, branch="tfp", transition_id="focused_to_unstable",
    )
    assert outcome["outcome"] == "collect_evidence"
    assert "rule_dominance_transition" in outcome.get("missing_evidence", [])


def test_unknown_transition_id_yields_abstain(monkeypatch):
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ACT_ENABLED", "1")
    result = make_pipeline_result()
    outcome = attempt_hesperia_transition(
        result, branch="cobalt", transition_id="not_a_real_transition",
    )
    assert outcome["outcome"] == "denied"


def test_stateless_same_input_same_outcome(monkeypatch):
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ACT_ENABLED", "1")
    result = make_pipeline_result()
    o1 = attempt_hesperia_transition(result, branch="tfp", transition_id="focused_to_unstable")
    o2 = attempt_hesperia_transition(result, branch="tfp", transition_id="focused_to_unstable")
    assert o1 == o2
