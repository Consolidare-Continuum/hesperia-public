"""Map fpf-thinking-map MCP outcome JSON into router envelope blocks."""

from __future__ import annotations

from typing import Any


def logic_mapping_from_thinking_map(outcome: dict[str, Any]) -> dict[str, Any]:
    """Extract logic_mapping from thinking_map_step JSON (library canonical)."""
    llm = outcome.get("llm_prompt_state") or {}
    logic = llm.get("logic")
    if isinstance(logic, dict):
        return logic
    return {"facts": [], "actions": [], "source": "fpf-thinking-map"}


def policy_block_from_thinking_map(outcome: dict[str, Any]) -> dict[str, Any]:
    """Build policy_block from gate_status, missing_evidence, outcome kind.

    FPF-MWI-04: also pass through ``possible_transitions`` and ``response_contract``
    when present on the library outcome / llm_prompt_state (no Hesperia-side enforcement).
    """
    llm = outcome.get("llm_prompt_state") or {}
    block: dict[str, Any] = {
        "outcome_kind": outcome.get("kind"),
        "reason": outcome.get("reason"),
        "missing_evidence": outcome.get("missing_evidence") or llm.get("missing_evidence") or [],
        "gate_status": llm.get("gate_status") or {},
        "risk_level": llm.get("risk_level"),
        "blockers": outcome.get("blockers"),
        "source": "fpf-thinking-map",
    }
    transitions = outcome.get("possible_transitions") or llm.get("possible_transitions")
    if transitions is not None:
        block["possible_transitions"] = transitions
    response_contract = outcome.get("response_contract") or llm.get("response_contract")
    if response_contract is not None:
        block["response_contract"] = response_contract
    return block
