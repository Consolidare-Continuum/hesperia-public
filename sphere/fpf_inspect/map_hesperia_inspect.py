# HESPERIA — domain map hesperia_inspect (FPF-BUII-05).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""SemanticMap for bottom-up dig: l0_hash → layer_climb → gap_named → advise_or_escalate → idle."""

from __future__ import annotations

from typing import Any

from fpf_thinking_map.primitives import (
    AgencyLevel,
    ContextPrimitive,
    EvidencePrimitive,
    FGR,
    Freshness,
    GateCheck,
    GatePrimitive,
    RolePrimitive,
    TransitionPrimitive,
)
from fpf_thinking_map.state import RuntimeBinding, SemanticMap
from fpf_thinking_map.traversal import ThinkingMapTraversal


def build_hesperia_inspect_map() -> SemanticMap:
    sm = SemanticMap()
    ctx = "hesperia_inspect"
    sm.register_context(
        ContextPrimitive(
            context_id=ctx,
            label="Hesperia FPF bottom-up inspect",
            glossary={
                "dig": "climb sealed engine layers via fpf_inspect",
                "gap": "named GapReport entry — not free-form evidence",
                "provisional": "ADR tag until Option B / 40_POLICY / anchor_map_v1 freeze",
            },
            invariants=[
                "inspect never mutates sealed engine",
                "upper LLM narrative layer stays separate",
                "L6 stubs never EvidencePrimitive",
            ],
        )
    )
    sm.register_role(
        RolePrimitive(
            role_id="digger",
            label="Inspect digger",
            context_id=ctx,
            agency_level=AgencyLevel.DELIBERATIVE,
            responsibilities=["probe layers", "emit GapReport", "advise without fabricating evidence"],
        )
    )
    for eid, label in (
        ("analyze_fingerprint", "L0 analyze + fingerprint"),
        ("inspect_slice_done", "At least one InspectSlice produced"),
        ("gap_report_done", "GapReport v0.1 emitted"),
        ("provisional_ack", "Provisional ADR tags acknowledged"),
    ):
        sm.register_evidence(
            EvidencePrimitive(
                evidence_id=eid,
                label=label,
                context_id=ctx,
                claim=label,
                source="sphere.fpf_inspect",
                fgr=FGR(formality=0.9, scope=0.85, reliability=0.9),
                freshness=Freshness.CURRENT,
            )
        )
    sm.register_gate(
        GatePrimitive(
            gate_id="dig_ready",
            label="Dig ready",
            context_id=ctx,
            checks=[
                GateCheck(
                    check_id="has_fingerprint",
                    description="analyze fingerprint present",
                    required_evidence=["analyze_fingerprint"],
                )
            ],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_climb",
            label="Start layer climb",
            context_id=ctx,
            from_state="l0_hash",
            to_state="layer_climb",
            required_evidence=["analyze_fingerprint"],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_gap",
            label="Name gap",
            context_id=ctx,
            from_state="layer_climb",
            to_state="gap_named",
            required_evidence=["inspect_slice_done"],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_advise",
            label="Advise or escalate",
            context_id=ctx,
            from_state="gap_named",
            to_state="advise_or_escalate",
            required_evidence=["gap_report_done"],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_idle",
            label="Idle",
            context_id=ctx,
            from_state="advise_or_escalate",
            to_state="idle",
            required_evidence=["provisional_ack"],
        )
    )
    return sm


def map_step(
    *,
    current_state: str = "l0_hash",
    current_evidence: str = "",
    task: str = "hesperia dig",
    actor_role_ids: str = "digger",
) -> dict[str, Any]:
    """One thinking_map_step over hesperia_inspect — JSON-serializable outcome."""
    sm = build_hesperia_inspect_map()
    engine = ThinkingMapTraversal(sm)
    evidence_tokens = [t.strip() for t in current_evidence.replace(",", " ").split() if t.strip()]
    roles = [r.strip() for r in actor_role_ids.split(",") if r.strip()] or ["digger"]
    binding = RuntimeBinding(
        task=task,
        actor_role_ids=roles,
        active_context_id="hesperia_inspect",
        current_evidence=evidence_tokens,
    )
    state = engine.build_active_state(binding, current_state=current_state)
    outcome = engine.step(state)
    llm = getattr(outcome, "llm_prompt_state", None)
    return {
        "kind": str(outcome.kind),
        "reason": getattr(outcome, "reason", ""),
        "next_state": getattr(outcome, "next_state", None),
        "missing_evidence": getattr(outcome, "missing_evidence", None),
        "blockers": getattr(outcome, "blockers", None),
        "llm_prompt_state": llm,
        "map_id": "hesperia_inspect",
    }
