# HESPERIA — fpf-thinking-map calibration SemanticMap (FPF-V7-13).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Hesperia TFP LLM calibration map — gate before structured provider calls."""

from __future__ import annotations

from fpf_thinking_map.logic import DecisionRule, EvidencePresent, LogicLayer, RuleKind
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
from fpf_thinking_map.state import SemanticMap


def build_calibration_map() -> SemanticMap:
    sm = SemanticMap()

    sm.register_context(
        ContextPrimitive(
            context_id="hesperia_calibration",
            label="Hesperia TFP LLM Calibration",
            glossary={
                "calibration_task": "dict_a | areas | topology tool identity",
                "segment_substrate": "bounded segment payload for one LLM call",
                "schema_bound": "JSON schema contract attached to call",
            },
            invariants=[
                "thinking-map step runs before each structured LLM calibration call",
                "prompt substrate is JSON envelope — not ad-hoc prose authority",
                "dry_run bypasses provider but not map step",
            ],
        )
    )

    sm.register_role(
        RolePrimitive(
            role_id="calibration_runner",
            label="Calibration Runner",
            context_id="hesperia_calibration",
            agency_level=AgencyLevel.DELIBERATIVE,
            responsibilities=["run governed calibration LLM calls"],
        )
    )

    for eid, label in (
        ("calibration_task", "Calibration tool id (dict_a, areas, topology)"),
        ("segment_substrate", "Segment-level calibration substrate"),
        ("schema_bound", "Structured output schema bound to call"),
        ("openai_api_key", "OPENAI_API_KEY present in environment"),
        ("dry_run", "Dry-run mode — no provider call"),
    ):
        sm.register_evidence(
            EvidencePrimitive(
                evidence_id=eid,
                label=label,
                context_id="hesperia_calibration",
                claim=label,
                source="calibration CLI",
                fgr=FGR(formality=0.85, scope=0.85, reliability=0.9),
                freshness=Freshness.CURRENT,
            )
        )

    sm.register_gate(
        GatePrimitive(
            gate_id="provider_gate",
            label="LLM provider gate",
            context_id="hesperia_calibration",
            checks=[
                GateCheck(
                    check_id="provider_or_dry",
                    description="OpenAI key or dry_run",
                    required_evidence=["openai_api_key"],
                ),
            ],
        )
    )

    sm.register_transition(
        TransitionPrimitive(
            transition_id="invoke_llm",
            label="Invoke governed calibration LLM",
            context_id="hesperia_calibration",
            from_state="start",
            to_state="llm_invoked",
            required_evidence=["calibration_task", "segment_substrate", "schema_bound"],
            required_gate_id="provider_gate",
        )
    )

    return sm


def build_calibration_logic() -> LogicLayer:
    logic = LogicLayer()
    logic.add_rule(
        DecisionRule(
            name="dry_run_bypass",
            condition=EvidencePresent("dry_run"),
            action_if_true="skip_provider_gate",
            action_if_false="require_provider",
            kind=RuleKind.ROUTE,
            tags=["hesperia_calibration"],
        )
    )
    return logic
