# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Static structural state graph — TransitionPrimitive network derived from state_classifier.py."""

from __future__ import annotations

from fpf_thinking_map.primitives import (
    GateCheck,
    GatePrimitive,
    TransitionPrimitive,
)

from sphere.fpf_bridge.constants import (
    CONTEXT_ID,
    STATE_FOCUSED_DOMINANT,
    STATE_DISTRIBUTED_BALANCED,
    STATE_UNSTABLE_TRANSITION,
    STATE_TENSION_ELEVATED,
    STATE_DIFFUSE_SPREAD,
)


def build_structural_gates(context_id: str = CONTEXT_ID) -> list[GatePrimitive]:
    """Gates for structural state transitions — evidence requirements per move."""
    return [
        GatePrimitive(
            gate_id="gate_dominance_shift",
            label="Dominance shift gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_entropy_increase",
                    description="Entropy must increase to leave focused dominance",
                    required_evidence=["rule_entropy_drop"],
                ),
            ],
            fail_closed=False,
        ),
        GatePrimitive(
            gate_id="gate_dominance_transition",
            label="Dominance transition gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_dominance_transition_event",
                    description="Dominance transition event must be detected",
                    required_evidence=["rule_dominance_transition"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_tension_increase",
            label="Tension increase gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_tension_event",
                    description="Tension increase event must be detected",
                    required_evidence=["rule_tension_increase"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_propagation_spread",
            label="Propagation spread gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_propagation_event",
                    description="Propagation spread event must be detected",
                    required_evidence=["rule_propagation_spread"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_stability_recovery",
            label="Stability recovery gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_stability_evidence",
                    description="Stability evidence must be present for recovery",
                    required_evidence=["stability_sufficient"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_focus_emergence",
            label="Focus emergence gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_dominant_area",
                    description="Dominant area must be detected",
                    required_evidence=["rule_dominant_area"],
                ),
                GateCheck(
                    check_id="chk_entropy_drop",
                    description="Entropy must drop for focus to emerge",
                    required_evidence=["rule_entropy_drop"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_tension_reduction",
            label="Tension reduction gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_tension_reduced",
                    description="Tension must be reduced",
                    required_evidence=["tension_reduced"],
                ),
            ],
            fail_closed=True,
        ),
        GatePrimitive(
            gate_id="gate_propagation_controlled",
            label="Propagation controlled gate",
            context_id=context_id,
            checks=[
                GateCheck(
                    check_id="chk_propagation_controlled",
                    description="Propagation must be contained",
                    required_evidence=["propagation_controlled"],
                ),
            ],
            fail_closed=True,
        ),
    ]


def build_structural_state_graph(context_id: str = CONTEXT_ID) -> list[TransitionPrimitive]:
    """Static transition graph for the 5 structural states.

    Derived from sphere/interpretation/state_classifier.py classification logic.
    Each transition is gated by evidence requirements.
    """
    return [
        # From focused_dominant
        TransitionPrimitive(
            transition_id="focused_to_distributed",
            label="Dominance weakens → distributed balance",
            context_id=context_id,
            from_state=STATE_FOCUSED_DOMINANT,
            to_state=STATE_DISTRIBUTED_BALANCED,
            required_gate_id="gate_dominance_shift",
            required_evidence=["rule_entropy_drop"],
        ),
        TransitionPrimitive(
            transition_id="focused_to_unstable",
            label="Dominance transition detected",
            context_id=context_id,
            from_state=STATE_FOCUSED_DOMINANT,
            to_state=STATE_UNSTABLE_TRANSITION,
            required_gate_id="gate_dominance_transition",
            required_evidence=["rule_dominance_transition"],
        ),
        TransitionPrimitive(
            transition_id="focused_to_tension",
            label="Tension rises under focused dominance",
            context_id=context_id,
            from_state=STATE_FOCUSED_DOMINANT,
            to_state=STATE_TENSION_ELEVATED,
            required_gate_id="gate_tension_increase",
            required_evidence=["rule_tension_increase"],
        ),
        # From distributed_balanced
        TransitionPrimitive(
            transition_id="distributed_to_focused",
            label="Focus emerges from distributed state",
            context_id=context_id,
            from_state=STATE_DISTRIBUTED_BALANCED,
            to_state=STATE_FOCUSED_DOMINANT,
            required_gate_id="gate_focus_emergence",
            required_evidence=["rule_dominant_area", "rule_entropy_drop"],
        ),
        TransitionPrimitive(
            transition_id="distributed_to_diffuse",
            label="Propagation spreads from distributed state",
            context_id=context_id,
            from_state=STATE_DISTRIBUTED_BALANCED,
            to_state=STATE_DIFFUSE_SPREAD,
            required_gate_id="gate_propagation_spread",
            required_evidence=["rule_propagation_spread"],
        ),
        TransitionPrimitive(
            transition_id="distributed_to_tension",
            label="Tension rises in distributed state",
            context_id=context_id,
            from_state=STATE_DISTRIBUTED_BALANCED,
            to_state=STATE_TENSION_ELEVATED,
            required_gate_id="gate_tension_increase",
            required_evidence=["rule_tension_increase"],
        ),
        # From unstable_transition
        TransitionPrimitive(
            transition_id="unstable_to_focused",
            label="Instability resolves into focus",
            context_id=context_id,
            from_state=STATE_UNSTABLE_TRANSITION,
            to_state=STATE_FOCUSED_DOMINANT,
            required_gate_id="gate_stability_recovery",
            required_evidence=["stability_sufficient"],
        ),
        TransitionPrimitive(
            transition_id="unstable_to_distributed",
            label="Instability resolves into balance",
            context_id=context_id,
            from_state=STATE_UNSTABLE_TRANSITION,
            to_state=STATE_DISTRIBUTED_BALANCED,
            required_gate_id="gate_stability_recovery",
            required_evidence=["stability_sufficient"],
        ),
        TransitionPrimitive(
            transition_id="unstable_to_tension",
            label="Instability escalates to tension",
            context_id=context_id,
            from_state=STATE_UNSTABLE_TRANSITION,
            to_state=STATE_TENSION_ELEVATED,
            required_gate_id="gate_tension_increase",
            required_evidence=["rule_tension_increase"],
        ),
        # From tension_elevated
        TransitionPrimitive(
            transition_id="tension_to_distributed",
            label="Tension resolves into balance",
            context_id=context_id,
            from_state=STATE_TENSION_ELEVATED,
            to_state=STATE_DISTRIBUTED_BALANCED,
            required_gate_id="gate_tension_reduction",
            required_evidence=["tension_reduced"],
        ),
        TransitionPrimitive(
            transition_id="tension_to_unstable",
            label="Tension triggers dominance transition",
            context_id=context_id,
            from_state=STATE_TENSION_ELEVATED,
            to_state=STATE_UNSTABLE_TRANSITION,
            required_gate_id="gate_dominance_transition",
            required_evidence=["rule_dominance_transition"],
        ),
        # From diffuse_spread
        TransitionPrimitive(
            transition_id="diffuse_to_distributed",
            label="Diffusion contained → balance",
            context_id=context_id,
            from_state=STATE_DIFFUSE_SPREAD,
            to_state=STATE_DISTRIBUTED_BALANCED,
            required_gate_id="gate_propagation_controlled",
            required_evidence=["propagation_controlled"],
        ),
        TransitionPrimitive(
            transition_id="diffuse_to_focused",
            label="Focus emerges from diffusion",
            context_id=context_id,
            from_state=STATE_DIFFUSE_SPREAD,
            to_state=STATE_FOCUSED_DOMINANT,
            required_gate_id="gate_focus_emergence",
            required_evidence=["rule_dominant_area", "rule_entropy_drop"],
        ),
    ]
