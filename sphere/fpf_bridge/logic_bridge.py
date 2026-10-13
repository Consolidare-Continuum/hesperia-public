# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Maps L9 rules + prolog derived facts to fpf LogicLayer."""

from __future__ import annotations

from typing import Any

from fpf_thinking_map.logic import (
    CustomProp,
    DecisionRule,
    EvidencePresent,
    HasMissingEvidence,
    InState,
    LogicLayer,
    RiskAbove,
    RuleKind,
)

from sphere.fpf_bridge.constants import STATE_FOCUSED_DOMINANT, CONTRADICTION_PRESSURE_NOTABLE


def _prolog_prop(fact_name: str, derived_facts: list[str]) -> CustomProp:
    """Pre-resolved boolean — no prolog re-execution."""
    present = fact_name in derived_facts
    return CustomProp(f"prolog_{fact_name}", lambda _state, _p=present: _p)


def build_hesperia_logic_layer(
    logic_metrics: dict[str, Any],
    interpretation_metrics: dict[str, Any],
    prolog_logic: dict[str, Any],
    l5_metrics: dict[str, Any] | None = None,
) -> LogicLayer:
    """Build fpf LogicLayer from sphere L9/L9b/L10 outputs."""
    derived = []
    for fact in prolog_logic.get("derived_facts", []):
        if isinstance(fact, str):
            derived.append(fact)
        elif isinstance(fact, dict):
            p = fact.get("predicate", "")
            if p:
                derived.append(p)

    logic = LogicLayer()

    # Rule 1: elevated risk → escalate (BLOCK)
    logic.add_rule(DecisionRule(
        name="elevated_risk",
        condition=_prolog_prop("elevated_risk", derived),
        action_if_true="escalate_review",
        explanation="Prolog derived elevated_risk — tension + dominance transition co-occur",
        kind=RuleKind.BLOCK,
        tags=["structural", "risk"],
        risk_sensitive=True,
    ))

    # Rule 1b (fpf_bridge v7.2 pilot): contradiction pressure notable → block (BLOCK)
    # NOTE on enforcement: same as Rule 1 (elevated_risk), RuleKind.BLOCK here is a label the
    # LLM-facing prompt carries (kind="block" in to_llm_context) — LogicLayer.evaluate does not
    # itself prevent a transition from firing. Real, code-enforced blocking (not just labeling)
    # is v7.3's responsibility (attempt_hesperia_transition), which can check this rule's
    # `satisfied` output directly and refuse to report the associated conclusion as settled.
    if l5_metrics:
        pressure = l5_metrics.get("CONTRADICTION_PRESSURE_SCORE")
        pressure_notable = pressure is not None and float(pressure) >= CONTRADICTION_PRESSURE_NOTABLE
        gate_failed = not bool(l5_metrics.get("REALITY_GATE_COUNTER_EVIDENCE", True))
        logic.add_rule(DecisionRule(
            name="contradiction_pressure_high",
            condition=CustomProp(
                "contradiction_notable",
                lambda _state, _v=(pressure_notable or gate_failed): _v,
            ),
            action_if_true="avoid_conclusion_pending_review",
            explanation="Counter-evidence pressure is notable or its policy gate failed — do not narrate a settled conclusion",
            kind=RuleKind.BLOCK,
            tags=["structural", "contradiction"],
            risk_sensitive=False,
        ))

    # Rule 2: structural focus → deep dive (HINT)
    logic.add_rule(DecisionRule(
        name="structural_focus",
        condition=InState(STATE_FOCUSED_DOMINANT).AND(
            _prolog_prop("structural_focus", derived),
        ),
        action_if_true="area_deep_dive",
        explanation="Focused dominant state with structural focus — investigate dominant area",
        kind=RuleKind.HINT,
        tags=["structural"],
    ))

    # Rule 3: propagation wave → review scope (WARN)
    logic.add_rule(DecisionRule(
        name="propagation_wave",
        condition=_prolog_prop("propagation_wave", derived),
        action_if_true="review_diffusion_scope",
        explanation="Propagation wave detected — activation spreading across areas",
        kind=RuleKind.WARN,
        tags=["structural", "propagation"],
    ))

    # Rule 4: transition risk → compare with previous (ROUTE)
    logic.add_rule(DecisionRule(
        name="transition_risk",
        condition=_prolog_prop("transition_risk", derived),
        action_if_true="compare_with_previous",
        explanation="Dominance transition risk — compare with prior structural state",
        kind=RuleKind.ROUTE,
        tags=["structural", "transition"],
    ))

    # Rule 5: high risk + tension + missing evidence → collect (WARN, IMPLIES)
    logic.add_rule(DecisionRule(
        name="risk_evidence_gap",
        condition=RiskAbove("high").AND(
            InState("tension_elevated"),
        ).IMPLIES(HasMissingEvidence()),
        action_if_true="collect_additional_evidence",
        explanation="High risk + tension → evidence gaps must be filled before proceeding",
        kind=RuleKind.WARN,
        tags=["structural", "risk"],
        risk_sensitive=True,
    ))

    # Rule 6: focused_dominant IFF dominant_area evidence (HINT, IFF)
    logic.add_rule(DecisionRule(
        name="state_evidence_alignment",
        condition=InState(STATE_FOCUSED_DOMINANT).IFF(
            EvidencePresent("rule_dominant_area"),
        ),
        action_if_true="state_evidence_aligned",
        action_if_false="state_evidence_mismatch",
        explanation="Structural state should align with evidence — mismatch signals classification issue",
        kind=RuleKind.HINT,
        tags=["structural", "readiness"],
    ))

    # Rule 7: propagation_spread XOR dominant_area (HINT, XOR)
    logic.add_rule(DecisionRule(
        name="spread_vs_focus",
        condition=EvidencePresent("rule_propagation_spread").XOR(
            EvidencePresent("rule_dominant_area"),
        ),
        action_if_true="single_structural_pattern",
        action_if_false="mixed_structural_pattern",
        explanation="Exactly one of spread/focus active = clean pattern; both/neither = mixed",
        kind=RuleKind.HINT,
        tags=["structural"],
    ))

    return logic
