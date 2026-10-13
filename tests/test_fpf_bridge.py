# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# See LEGAL_NOTICE.md for full terms.

"""Tests for sphere/fpf_bridge — deterministic, no LLM required."""

from __future__ import annotations

import copy
import json

import pytest

from fpf_thinking_map.primitives import Freshness, GateDecision
from fpf_thinking_map.traversal import OutcomeKind

from sphere.fpf_bridge.bridge import bridge_pipeline_result, bridge_to_llm_prompt
from sphere.fpf_bridge.constants import (
    ALL_STATES,
    CONTEXT_ID,
    STATE_DISTRIBUTED_BALANCED,
    STATE_FOCUSED_DOMINANT,
    STATE_TENSION_ELEVATED,
    STATE_UNSTABLE_TRANSITION,
    STATE_DIFFUSE_SPREAD,
    STATE_RISK_MAP,
)
from sphere.fpf_bridge.evidence_mapper import (
    collect_all_evidence,
    map_stability_to_freshness,
    map_triggered_rules_to_evidence,
)
from sphere.fpf_bridge.guard_bridge import build_hesperia_guards
from sphere.fpf_bridge.logic_bridge import build_hesperia_logic_layer
from sphere.fpf_bridge.state_graph import build_structural_state_graph

from tests.fixtures.mock_pipeline_result import make_pipeline_result


# ---------------------------------------------------------------------------
# State graph
# ---------------------------------------------------------------------------

class TestStateGraph:
    def test_all_states_have_outgoing_transitions(self):
        transitions = build_structural_state_graph()
        states_with_outgoing = {t.from_state for t in transitions}
        assert states_with_outgoing == ALL_STATES

    def test_graph_is_connected(self):
        transitions = build_structural_state_graph()
        reachable: set[str] = {STATE_FOCUSED_DOMINANT}
        changed = True
        while changed:
            changed = False
            for t in transitions:
                if t.from_state in reachable and t.to_state not in reachable:
                    reachable.add(t.to_state)
                    changed = True
        assert reachable == ALL_STATES

    def test_transition_count(self):
        transitions = build_structural_state_graph()
        assert len(transitions) == 13

    def test_all_transitions_have_context(self):
        for t in build_structural_state_graph():
            assert t.context_id == CONTEXT_ID


# ---------------------------------------------------------------------------
# Evidence mapper
# ---------------------------------------------------------------------------

class TestEvidenceMapper:
    def test_triggered_rules_produce_evidence(self):
        result = make_pipeline_result()
        evidence = map_triggered_rules_to_evidence(
            result["logic_metrics"], result["dynamism_metrics"],
        )
        ids = {e.evidence_id for e in evidence}
        assert "rule_dominant_area" in ids
        assert "rule_entropy_drop" in ids

    def test_high_share_gets_high_fgr(self):
        result = make_pipeline_result()
        evidence = map_triggered_rules_to_evidence(
            result["logic_metrics"], result["dynamism_metrics"],
        )
        dominant = next(e for e in evidence if e.evidence_id == "rule_dominant_area")
        assert dominant.fgr.formality >= 0.9

    def test_low_share_gets_low_fgr(self):
        result = make_pipeline_result(logic_metrics={
            "triggered_rules": [{"type": "dominant_area", "share": 0.2}],
            "anomaly_flags": [],
        })
        evidence = map_triggered_rules_to_evidence(
            result["logic_metrics"], result["dynamism_metrics"],
        )
        dominant = next(e for e in evidence if e.evidence_id == "rule_dominant_area")
        assert dominant.fgr.formality <= 0.7

    def test_stability_to_freshness_current(self):
        assert map_stability_to_freshness({"stability_index": 0.8}) == Freshness.CURRENT

    def test_stability_to_freshness_stale(self):
        assert map_stability_to_freshness({"stability_index": 0.5}) == Freshness.STALE

    def test_stability_to_freshness_expired(self):
        assert map_stability_to_freshness({"stability_index": 0.1}) == Freshness.EXPIRED

    def test_stability_boundary_current(self):
        assert map_stability_to_freshness({"stability_index": 0.7}) == Freshness.CURRENT

    def test_stability_boundary_stale(self):
        assert map_stability_to_freshness({"stability_index": 0.3}) == Freshness.STALE

    def test_area_activations_produce_evidence(self):
        result = make_pipeline_result()
        all_ev = collect_all_evidence(
            result["logic_metrics"], result["shadow_metrics"], result["dynamism_metrics"],
        )
        area_ev = [e for e in all_ev if e.evidence_id.startswith("area_")]
        assert len(area_ev) == 12

    def test_zero_area_excluded(self):
        result = make_pipeline_result(shadow_metrics={
            "corrected_area_vector": [0.0, 0.0, 1.0] + [0.0] * 9,
            "shadow_diagnostics": {},
        })
        all_ev = collect_all_evidence(
            result["logic_metrics"], result["shadow_metrics"], result["dynamism_metrics"],
        )
        area_ev = [e for e in all_ev if e.evidence_id.startswith("area_")]
        assert len(area_ev) == 1
        assert area_ev[0].evidence_id == "area_A2_activation"


# ---------------------------------------------------------------------------
# Guard bridge
# ---------------------------------------------------------------------------

class TestGuardBridge:
    def test_all_pass(self):
        result = make_pipeline_result()
        guards = build_hesperia_guards(result["guards"])
        assert len(guards) == 3
        from fpf_thinking_map.state import ActiveState, SemanticMap, RuntimeBinding
        dummy_state = ActiveState(SemanticMap(), RuntimeBinding())
        for g in guards:
            r = g.evaluate(dummy_state)
            assert r.verdict.value == "allow"

    def test_sigma_failure_denies(self):
        result = make_pipeline_result(guards={
            "sigma": {"passed": False, "failed_checks": [{"message": "invariant_broken"}]},
            "gamma": {"passed": True, "failed_checks": []},
            "theta": {"approved": True, "warnings": [], "violations": []},
        })
        guards = build_hesperia_guards(result["guards"])
        from fpf_thinking_map.state import ActiveState, SemanticMap, RuntimeBinding
        dummy = ActiveState(SemanticMap(), RuntimeBinding())
        sigma = guards[0]
        r = sigma.evaluate(dummy)
        assert r.verdict.value == "deny"
        assert "invariant_broken" in r.reason

    def test_theta_warning(self):
        result = make_pipeline_result(guards={
            "sigma": {"passed": True, "failed_checks": []},
            "gamma": {"passed": True, "failed_checks": []},
            "theta": {"approved": True, "warnings": ["NON_CANONICAL"], "violations": []},
        })
        guards = build_hesperia_guards(result["guards"])
        from fpf_thinking_map.state import ActiveState, SemanticMap, RuntimeBinding
        dummy = ActiveState(SemanticMap(), RuntimeBinding())
        theta = guards[2]
        r = theta.evaluate(dummy)
        assert r.verdict.value == "warn"
        assert "NON_CANONICAL" in r.reason

    def test_theta_denial(self):
        result = make_pipeline_result(guards={
            "sigma": {"passed": True, "failed_checks": []},
            "gamma": {"passed": True, "failed_checks": []},
            "theta": {"approved": False, "warnings": [], "violations": ["quarantine"]},
        })
        guards = build_hesperia_guards(result["guards"])
        from fpf_thinking_map.state import ActiveState, SemanticMap, RuntimeBinding
        dummy = ActiveState(SemanticMap(), RuntimeBinding())
        theta = guards[2]
        r = theta.evaluate(dummy)
        assert r.verdict.value == "deny"


# ---------------------------------------------------------------------------
# Logic bridge
# ---------------------------------------------------------------------------

class TestLogicBridge:
    def test_structural_focus_fires(self):
        result = make_pipeline_result()
        logic = build_hesperia_logic_layer(
            result["logic_metrics"], result["interpretation_metrics"], result["prolog_logic"],
        )
        _, state = bridge_pipeline_result(result)
        actions = logic.satisfied_actions(state)
        assert "area_deep_dive" in actions

    def test_elevated_risk_blocks(self):
        result = make_pipeline_result(prolog_logic={
            "derived_facts": [
                {"predicate": "elevated_risk", "args": []},
                {"predicate": "structural_focus", "args": []},
            ],
            "rule_traces": [],
            "prolog_diagnostics": {},
        })
        result["interpretation_metrics"]["structural_state"] = STATE_TENSION_ELEVATED
        logic = build_hesperia_logic_layer(
            result["logic_metrics"], result["interpretation_metrics"], result["prolog_logic"],
        )
        _, state = bridge_pipeline_result(result)
        actions = logic.satisfied_actions(state)
        assert "escalate_review" in actions

    def test_no_prolog_facts_no_actions(self):
        result = make_pipeline_result(prolog_logic={
            "derived_facts": [],
            "rule_traces": [],
            "prolog_diagnostics": {},
        })
        logic = build_hesperia_logic_layer(
            result["logic_metrics"], result["interpretation_metrics"], result["prolog_logic"],
        )
        _, state = bridge_pipeline_result(result)
        actions = logic.satisfied_actions(state)
        assert "escalate_review" not in actions
        assert "review_diffusion_scope" not in actions


# ---------------------------------------------------------------------------
# Full bridge
# ---------------------------------------------------------------------------

class TestBridge:
    def test_focused_dominant_state(self):
        result = make_pipeline_result()
        _, state = bridge_pipeline_result(result)
        assert state.current_state == STATE_FOCUSED_DOMINANT
        assert state.binding.risk_level == "normal"
        assert "structural_analyst" in [r.role_id for r in state.active_roles]
        assert state.active_context is not None

    def test_unstable_transition_high_risk(self):
        result = make_pipeline_result(interpretation_metrics={
            "structural_state": STATE_UNSTABLE_TRANSITION,
            "interpretation_flags": ["transition_risk"],
        })
        _, state = bridge_pipeline_result(result)
        assert state.current_state == STATE_UNSTABLE_TRANSITION
        assert state.binding.risk_level == "high"

    def test_distributed_balanced_low_risk(self):
        result = make_pipeline_result(interpretation_metrics={
            "structural_state": STATE_DISTRIBUTED_BALANCED,
            "interpretation_flags": [],
        })
        _, state = bridge_pipeline_result(result)
        assert state.binding.risk_level == "low"

    def test_transition_fires(self):
        result = make_pipeline_result()
        traversal, state = bridge_pipeline_result(result)
        outcome = traversal.attempt_transition(state, "focused_to_distributed")
        assert outcome.kind == OutcomeKind.CONTINUE
        assert state.current_state == STATE_DISTRIBUTED_BALANCED

    def test_invalid_transition_abstains(self):
        result = make_pipeline_result()
        traversal, state = bridge_pipeline_result(result)
        outcome = traversal.attempt_transition(state, "distributed_to_focused")
        assert outcome.kind == OutcomeKind.ABSTAIN

    def test_missing_evidence_transition(self):
        result = make_pipeline_result()
        traversal, state = bridge_pipeline_result(result)
        outcome = traversal.attempt_transition(state, "focused_to_unstable")
        assert outcome.kind == OutcomeKind.COLLECT_EVIDENCE
        assert "rule_dominance_transition" in outcome.missing_evidence

    def test_sigma_failure_blocks_traversal(self):
        result = make_pipeline_result(guards={
            "sigma": {"passed": False, "failed_checks": [{"message": "broken"}]},
            "gamma": {"passed": True, "failed_checks": []},
            "theta": {"approved": True, "warnings": [], "violations": []},
        })
        traversal, state = bridge_pipeline_result(result)
        outcome = traversal.step(state)
        assert "Sigma" in outcome.reason

    def test_determinism(self):
        result = make_pipeline_result()
        prompt1 = bridge_to_llm_prompt(result)
        prompt2 = bridge_to_llm_prompt(result)
        assert json.dumps(prompt1, sort_keys=True) == json.dumps(prompt2, sort_keys=True)

    def test_read_only(self):
        result = make_pipeline_result()
        original = copy.deepcopy(result)
        bridge_pipeline_result(result)
        assert json.dumps(result, sort_keys=True) == json.dumps(original, sort_keys=True)


# ---------------------------------------------------------------------------
# LLM prompt state
# ---------------------------------------------------------------------------

class TestLLMPromptState:
    def test_prompt_has_required_keys(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        required = {
            "active_context", "active_roles", "goal", "task",
            "current_state", "available_evidence", "possible_transitions",
            "risk_level", "logic", "initial_outcome",
        }
        assert required.issubset(set(prompt.keys()))

    def test_prompt_logic_has_structure(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        logic = prompt["logic"]
        assert "facts" in logic
        assert "actions" in logic
        assert "consistency" in logic
        assert logic["consistency"]["consistent"] is True

    def test_all_states_produce_valid_prompts(self):
        for state_name in ALL_STATES:
            result = make_pipeline_result(interpretation_metrics={
                "structural_state": state_name,
                "interpretation_flags": [],
            })
            prompt = bridge_to_llm_prompt(result)
            assert prompt["current_state"] == state_name
            assert prompt["risk_level"] == STATE_RISK_MAP[state_name]


# ---------------------------------------------------------------------------
# fpf_bridge v7.2 evidence expansion — contradiction pilot (spec:
# fpf_bridge_v7_2_evidence_expansion.md §5, §8 gold test)
# ---------------------------------------------------------------------------

class TestContradictionEvidenceExpansion:
    def test_flags_off_by_default_no_behavior_change(self, monkeypatch):
        monkeypatch.delenv("HESPERIA_FPF_EVIDENCE_EXPANSION", raising=False)
        monkeypatch.delenv("HESPERIA_FPF_CONTRADICTION_GATE", raising=False)
        result = make_pipeline_result()
        result["layer_5"] = {
            "CONTRADICTION_PRESSURE_SCORE": 0.9,
            "REALITY_GATE_COUNTER_EVIDENCE": False,
            "ANTI_REGION_SIZE": 3,
        }
        prompt = bridge_to_llm_prompt(result)
        assert "contradiction_pressure" not in prompt["available_evidence"]
        assert not any(
            a["rule"] == "contradiction_pressure_high" for a in prompt["logic"]["actions"]
        )

    def test_high_pressure_surfaces_evidence_and_block_action(self, monkeypatch):
        monkeypatch.setenv("HESPERIA_FPF_EVIDENCE_EXPANSION", "1")
        monkeypatch.setenv("HESPERIA_FPF_CONTRADICTION_GATE", "1")
        result = make_pipeline_result()
        result["layer_5"] = {
            "CONTRADICTION_PRESSURE_SCORE": 0.8,
            "REALITY_GATE_COUNTER_EVIDENCE": False,
            "ANTI_REGION_SIZE": 3,
        }
        prompt = bridge_to_llm_prompt(result)
        assert "contradiction_pressure" in prompt["available_evidence"]
        assert "counter_evidence_gate" in prompt["available_evidence"]
        block_actions = [
            a for a in prompt["logic"]["actions"]
            if a["rule"] == "contradiction_pressure_high" and a["satisfied"]
        ]
        assert block_actions, "contradiction_pressure_high must fire when pressure exceeds cap"
        assert block_actions[0]["kind"] == "block"

    def test_low_pressure_emits_no_contradiction_evidence(self, monkeypatch):
        monkeypatch.setenv("HESPERIA_FPF_EVIDENCE_EXPANSION", "1")
        monkeypatch.setenv("HESPERIA_FPF_CONTRADICTION_GATE", "1")
        result = make_pipeline_result()
        result["layer_5"] = {
            "CONTRADICTION_PRESSURE_SCORE": 0.1,
            "REALITY_GATE_COUNTER_EVIDENCE": True,
        }
        prompt = bridge_to_llm_prompt(result)
        assert "contradiction_pressure" not in prompt["available_evidence"]

    def test_contradicts_field_populated_when_anti_region_present(self):
        from sphere.fpf_bridge.evidence_mapper import map_contradiction_to_evidence

        l5 = {
            "CONTRADICTION_PRESSURE_SCORE": 0.8,
            "REALITY_GATE_COUNTER_EVIDENCE": False,
            "ANTI_REGION_SIZE": 2,
        }
        evidence = map_contradiction_to_evidence(l5, {"stability_index": 0.6}, "test_ctx")
        pressure_ev = next(e for e in evidence if e.evidence_id == "contradiction_pressure")
        assert pressure_ev.contradicts == ["rule_dominant_area"]

    def test_l7_l4_evidence_surfaces_when_flag_on(self, monkeypatch):
        monkeypatch.setenv("HESPERIA_FPF_EVIDENCE_EXPANSION", "1")
        result = make_pipeline_result()
        result["layer_7"] = {
            "TRUST_TIER": 2, "SYSTEM_CONFIDENCE_SCORE": 0.61, "DECISION_STATUS_CODE": 20,
        }
        result["layer_4"] = {
            "EVIDENCE_SUPPORT_INDEX_BASELINE": 0.7, "INTEGRITY_CHECK_PASS_RATIO": 1.0,
        }
        prompt = bridge_to_llm_prompt(result)
        for eid in ("trust_tier", "system_confidence", "decision_status", "evidence_support_baseline"):
            assert eid in prompt["available_evidence"]

    def test_l7_l4_evidence_absent_when_flag_off(self, monkeypatch):
        monkeypatch.delenv("HESPERIA_FPF_EVIDENCE_EXPANSION", raising=False)
        result = make_pipeline_result()
        result["layer_7"] = {"TRUST_TIER": 2, "SYSTEM_CONFIDENCE_SCORE": 0.61, "DECISION_STATUS_CODE": 20}
        prompt = bridge_to_llm_prompt(result)
        assert "trust_tier" not in prompt["available_evidence"]

    def test_kme_and_triz_evidence_surface_when_flags_on(self, monkeypatch):
        """Phase 3/4: branch-scoped (tfp/cobalt) evidence surfaces in available_evidence even
        though its context_id differs from the run's active (core) context — proves the
        bounded-context registration in _build_semantic_map doesn't filter evidence availability,
        only transition/gate legality."""
        monkeypatch.setenv("HESPERIA_FPF_KME_EVIDENCE", "1")
        monkeypatch.setenv("HESPERIA_FPF_EVIDENCE_EXPANSION", "1")
        result = make_pipeline_result()
        result["kme"] = {
            "primitive_map": {"LD": 0.6, "COH": 0.7, "NC": 0.5, "PR": 0.4, "PV": 0.3, "CI": 0.2},
            "derived_map": {"KSI": 0.55},
            "triz_signals": {
                "contradictions": [{"contradiction_score": 0.8, "triz_principle": "segmentation"}],
            },
        }
        prompt = bridge_to_llm_prompt(result)
        for eid in ("kme_ld", "kme_coh", "kme_nc", "kme_pr", "kme_pv", "kme_ci", "kme_ksi", "triz_contradiction_0"):
            assert eid in prompt["available_evidence"], eid

    def test_kme_and_triz_evidence_absent_by_default(self, monkeypatch):
        monkeypatch.delenv("HESPERIA_FPF_KME_EVIDENCE", raising=False)
        monkeypatch.delenv("HESPERIA_FPF_EVIDENCE_EXPANSION", raising=False)
        result = make_pipeline_result()
        result["kme"] = {
            "primitive_map": {"LD": 0.6, "COH": 0.7, "NC": 0.5, "PR": 0.4, "PV": 0.3, "CI": 0.2},
            "derived_map": {"KSI": 0.55},
        }
        prompt = bridge_to_llm_prompt(result)
        assert "kme_ld" not in prompt["available_evidence"]
        assert "kme_ksi" not in prompt["available_evidence"]

    def test_kme_evidence_defaults_to_core_context_not_tfp(self):
        """Correction: KME is core Hesperia semantics (corners/kme.md) — bounded, domain-agnostic
        primitives over any activated concept graph. TFP was the first corpus it was validated
        against, not what it measures. Must not default to the TFP-only context."""
        from sphere.fpf_bridge.evidence_mapper import map_kme_primitives_to_evidence
        from sphere.fpf_bridge.constants import CONTEXT_ID, TFP_CONTEXT_ID

        primitive_map = {"LD": 0.6, "COH": 0.7, "NC": 0.5, "PR": 0.4, "PV": 0.3, "CI": 0.2}
        evidence = map_kme_primitives_to_evidence(primitive_map, {"KSI": 0.5}, {"stability_index": 0.6})
        assert all(e.context_id == CONTEXT_ID for e in evidence)
        assert all(e.context_id != TFP_CONTEXT_ID for e in evidence)

    def test_triz_evidence_defaults_to_core_context_not_cobalt(self):
        """Correction (same class as KME): TRIZ is also general-purpose Hesperia machinery —
        Altshuller's problem/contradiction/solution-path advisor, not COBALT-exclusive."""
        from sphere.fpf_bridge.evidence_mapper import map_triz_contradiction_to_evidence
        from sphere.fpf_bridge.constants import CONTEXT_ID, COBALT_CONTEXT_ID

        contradictions = [{"contradiction_score": 0.7, "triz_principle": "segmentation"}]
        evidence = map_triz_contradiction_to_evidence(contradictions, {"stability_index": 0.6})
        assert all(e.context_id == CONTEXT_ID for e in evidence)
        assert all(e.context_id != COBALT_CONTEXT_ID for e in evidence)

    def test_triz_never_shares_evidence_id_with_l5_contradiction(self, monkeypatch):
        """Namespace discipline (spec §2.1): triz_contradiction_* must never collide with, or be
        confused for, L5's contradiction_pressure — different mechanism, same English word."""
        monkeypatch.setenv("HESPERIA_FPF_EVIDENCE_EXPANSION", "1")
        result = make_pipeline_result()
        result["layer_5"] = {
            "CONTRADICTION_PRESSURE_SCORE": 0.8, "REALITY_GATE_COUNTER_EVIDENCE": False, "ANTI_REGION_SIZE": 1,
        }
        result["kme"] = {"triz_signals": {"contradictions": [{"contradiction_score": 0.5, "triz_principle": "counterbalance"}]}}
        prompt = bridge_to_llm_prompt(result)
        assert "contradiction_pressure" in prompt["available_evidence"]
        assert "triz_contradiction_0" in prompt["available_evidence"]
        assert "contradiction_pressure" != "triz_contradiction_0"
