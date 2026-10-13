# HESPERIA — Governed LLM calibration calls (FPF-V7-13).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""fpf-thinking-map step + governed prompt before OpenAI structured calibration."""

from __future__ import annotations

import json
import os
from typing import Any

from fpf_thinking_map.state import RuntimeBinding
from fpf_thinking_map.traversal import OutcomeKind, ThinkingMapTraversal

from sphere.calibration.thinking_map import build_calibration_logic, build_calibration_map
from sphere.router.thinking_map_bridge import logic_mapping_from_thinking_map, policy_block_from_thinking_map

_CALIBRATION_ENGINE: ThinkingMapTraversal | None = None

PAYLOAD_PREFIX = "HESPERIA_CALIBRATION_GOVERNED_JSON:\n"

_ALLOWED_OUTCOME_KINDS = frozenset(
    {
        "continue",
        "OutcomeKind.CONTINUE",
        "CONTINUE",
        "idle",
        "OutcomeKind.IDLE",
        "IDLE",
    }
)


def _engine() -> ThinkingMapTraversal:
    global _CALIBRATION_ENGINE
    if _CALIBRATION_ENGINE is None:
        _CALIBRATION_ENGINE = ThinkingMapTraversal(
            build_calibration_map(),
            logic_layer=build_calibration_logic(),
        )
    return _CALIBRATION_ENGINE


def outcome_to_dict(outcome: Any) -> dict[str, Any]:
    kind = outcome.kind
    kind_str = kind.value if hasattr(kind, "value") else str(kind)
    return {
        "kind": kind_str,
        "reason": getattr(outcome, "reason", ""),
        "missing_evidence": list(getattr(outcome, "missing_evidence", None) or []),
        "blockers": getattr(outcome, "blockers", None),
        "llm_prompt_state": getattr(outcome, "llm_prompt_state", None) or {},
    }


def calibration_evidence(*, dry_run: bool) -> list[str]:
    evidence = ["calibration_task", "segment_substrate", "schema_bound"]
    if dry_run:
        evidence.append("dry_run")
    elif os.environ.get("OPENAI_API_KEY"):
        evidence.append("openai_api_key")
    return evidence


def step_calibration_gate(
    *,
    tool: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Run one fpf-thinking-map step before a calibration LLM call."""
    engine = _engine()
    binding = RuntimeBinding(
        task=f"hesperia calibration {tool}",
        actor_role_ids=["calibration_runner"],
        active_context_id="hesperia_calibration",
        current_evidence=calibration_evidence(dry_run=dry_run),
    )
    state = engine.build_active_state(binding, current_state="start")
    outcome = engine.step(state, transition_id="invoke_llm")
    out = outcome_to_dict(outcome)
    out["tool"] = tool
    return out


def build_governed_calibration_prompt(
    *,
    tool: str,
    task_instructions: str,
    substrate: dict[str, Any],
    outcome: dict[str, Any],
) -> str:
    logic = logic_mapping_from_thinking_map(outcome)
    policy = policy_block_from_thinking_map(outcome)
    envelope = {
        "schema": "hesperia.calibration_prompt.v0_1",
        "tool": tool,
        "outcome_kind": outcome.get("kind"),
        "logic_mapping": logic,
        "policy_block": policy,
        "task_instructions": task_instructions.strip(),
        "substrate": substrate,
    }
    return PAYLOAD_PREFIX + json.dumps(envelope, sort_keys=True, ensure_ascii=False)


def _empty_for_schema(schema: dict[str, Any], substrate: dict[str, Any]) -> dict[str, Any]:
    required = schema.get("required") or []
    out: dict[str, Any] = {}
    for key in required:
        if key == "segment_id":
            out[key] = str(substrate.get("segment_id") or "")
        elif key == "concepts":
            out[key] = []
        elif key == "areas":
            areas = substrate.get("areas") or substrate.get("area_ids") or []
            out[key] = {a: 0.0 for a in areas} if isinstance(areas, list) else {}
        elif key == "dominant_area":
            areas = substrate.get("areas") or substrate.get("area_ids") or []
            out[key] = areas[0] if areas else ""
        elif key == "curve":
            out[key] = []
        else:
            out[key] = None
    return out


def call_governed_calibration(
    *,
    tool: str,
    task_instructions: str,
    substrate: dict[str, Any],
    schema: dict[str, Any],
    cfg: Any,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    HSR-V7 / FPF-V7-13: thinking-map gate → governed prompt → structured OpenAI call.

    On gate block or missing provider: returns schema-empty object (audit downstream as BLOCK).
    """
    outcome = step_calibration_gate(tool=tool, dry_run=dry_run)
    kind = str(outcome.get("kind") or "").lower()
    if dry_run:
        return _empty_for_schema(schema, substrate)
    if not os.environ.get("OPENAI_API_KEY"):
        return _empty_for_schema(schema, substrate)
    if kind not in {k.lower() for k in _ALLOWED_OUTCOME_KINDS}:
        return _empty_for_schema(schema, substrate)

    from tools.openai_calibration.openai_calibration_utils import StructuredCall, call_structured

    prompt = build_governed_calibration_prompt(
        tool=tool,
        task_instructions=task_instructions,
        substrate=substrate,
        outcome=outcome,
    )
    structured_cfg = cfg if isinstance(cfg, StructuredCall) else StructuredCall()
    result = call_structured(prompt, schema, cfg=structured_cfg)
    if not isinstance(result, dict):
        return _empty_for_schema(schema, substrate)
    return result
