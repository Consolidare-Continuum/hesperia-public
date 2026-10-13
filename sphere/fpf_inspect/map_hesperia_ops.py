# HESPERIA — domain map hesperia_ops (product agent rolling HAND).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Product rolling map — confirm runtime / inquire — separate from hesperia_inspect dig."""

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


def build_hesperia_ops_map() -> SemanticMap:
    sm = SemanticMap()
    ctx = "hesperia_ops"
    sm.register_context(
        ContextPrimitive(
            context_id=ctx,
            label="Hesperia FPF product ops (roll/act)",
            glossary={
                "roll": "invoke inquire/interpret via HAND",
                "inquire": "hesperia_router_inquire /product/interpret",
                "ground_truth": "engine logical/weight/source_activation",
            },
            invariants=[
                "engine authors ground_truth",
                "dig face stays on hesperia_inspect",
                "upper LLM narrative never evidence",
            ],
        )
    )
    sm.register_role(
        RolePrimitive(
            role_id="roller",
            label="Agent roller",
            context_id=ctx,
            agency_level=AgencyLevel.DELIBERATIVE,
            responsibilities=["confirm runtime", "inquire", "reattach ground_truth evidence"],
        )
    )
    for eid, label in (
        ("runtime_ok", "Hesperia runtime reachable"),
        ("inquire_done", "Router inquire / interpret returned"),
        ("ground_truth_ok", "Three ground_truth blocks present"),
        ("map_obeyed", "thinking_map_step outcome obeyed"),
    ):
        sm.register_evidence(
            EvidencePrimitive(
                evidence_id=eid,
                label=label,
                context_id=ctx,
                claim=label,
                source="sphere.fpf_inspect.hesperia_ops",
                fgr=FGR(formality=0.9, scope=0.85, reliability=0.9),
                freshness=Freshness.CURRENT,
            )
        )
    sm.register_gate(
        GatePrimitive(
            gate_id="runtime_gate",
            label="Runtime ready",
            context_id=ctx,
            checks=[
                GateCheck(
                    check_id="runtime",
                    description="runtime_ok",
                    required_evidence=["runtime_ok"],
                )
            ],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_inquire",
            label="Invoke inquire",
            context_id=ctx,
            from_state="start",
            to_state="inquire",
            required_evidence=["runtime_ok"],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_grounded",
            label="Attach ground_truth",
            context_id=ctx,
            from_state="inquire",
            to_state="grounded",
            required_evidence=["inquire_done"],
        )
    )
    sm.register_transition(
        TransitionPrimitive(
            transition_id="to_idle",
            label="Idle",
            context_id=ctx,
            from_state="grounded",
            to_state="idle",
            required_evidence=["ground_truth_ok", "map_obeyed"],
        )
    )
    return sm


def ops_map_step(
    *,
    current_state: str = "start",
    current_evidence: str = "",
    task: str = "hesperia roll",
    actor_role_ids: str = "roller",
) -> dict[str, Any]:
    sm = build_hesperia_ops_map()
    engine = ThinkingMapTraversal(sm)
    evidence_tokens = [t.strip() for t in current_evidence.replace(",", " ").split() if t.strip()]
    roles = [r.strip() for r in actor_role_ids.split(",") if r.strip()] or ["roller"]
    binding = RuntimeBinding(
        task=task,
        actor_role_ids=roles,
        active_context_id="hesperia_ops",
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
        "map_id": "hesperia_ops",
    }
