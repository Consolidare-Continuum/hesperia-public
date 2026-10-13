"""Gold test for fpf_bridge_v7_3 Phase 1: get_hesperia_bridge_state.

Spec: specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md §1.1, §8.
"""
from __future__ import annotations

import pytest

from runtime.agentic_bridge.get_state import (
    BridgeDisabledError,
    get_hesperia_bridge_state,
)
from tests.fixtures.mock_pipeline_result import make_pipeline_result


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HESPERIA_MCP_BRIDGE_ENABLED", raising=False)
    result = make_pipeline_result()
    with pytest.raises(BridgeDisabledError):
        get_hesperia_bridge_state(result, branch="tfp")


def test_branch_required_and_validated(monkeypatch):
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ENABLED", "1")
    result = make_pipeline_result()
    with pytest.raises(ValueError):
        get_hesperia_bridge_state(result, branch="mrt")  # type: ignore[arg-type]


def test_returns_bridge_state_shape_when_enabled(monkeypatch):
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ENABLED", "1")
    result = make_pipeline_result()
    state = get_hesperia_bridge_state(result, branch="tfp")
    assert state["branch"] == "tfp"
    required = {"current_state", "available_evidence", "possible_transitions", "logic", "initial_outcome"}
    assert required.issubset(state.keys())


def test_no_internal_llm_call_involved(monkeypatch):
    """The whole point of this tool vs mode='llm': no OpenAI/Anthropic call happens here —
    the caller (Cursor) is the reasoner, not Hesperia's own internal LLM integration."""
    monkeypatch.setenv("HESPERIA_MCP_BRIDGE_ENABLED", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = make_pipeline_result()
    # No API keys set — if this function tried to call an LLM, it would raise. It doesn't.
    state = get_hesperia_bridge_state(result, branch="cobalt")
    assert "current_state" in state
