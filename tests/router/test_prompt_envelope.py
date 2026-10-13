# Tests for HSR-V7-D-13/14: RouterPromptEnvelope builder + policy enforcement.

from __future__ import annotations

import pytest

from sphere.router.prompt_envelope import (
    PromptPolicyViolation,
    SCHEMA_ID,
    build_prompt_envelope,
    enforce_prompt_policy,
    enforce_prompt_policy_or_raise,
)


def _sample_input_envelope() -> dict:
    return {
        "schema": "hesperia.router_input_envelope.v0_1",
        "router_version": "v7-router-0.1",
        "input_hash": "a" * 64,
        "input_text": "raw user text must not appear in prompt envelope",
        "engine_trace": {"dominant_area_id": "A1", "governance": 0.5},
        "logic_mapping": {"source": "engine_analyze"},
        "retrieval_context": {"evidence_ids": ["ev-1"]},
        "relation_context": {},
        "policy_block": {"risk_level": "normal"},
        "corpus_snapshot_id": "corpus-v1",
        "policy_snapshot_id": "HSR-V7-01",
        "router_fingerprint": "f" * 64,
        "calculable": {"path_score": 0.2},
        "coherence_hints": {"hint": "bounded"},
    }


class TestBuildPromptEnvelope:
    def test_schema_and_subset(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        assert prompt["schema"] == SCHEMA_ID
        assert "input_text" not in prompt
        assert prompt["input_hash"] == "a" * 64
        assert prompt["engine_trace"]["dominant_area_id"] == "A1"
        assert prompt["allowed_tasks"]
        assert prompt["forbidden_actions"]
        assert prompt["answer_instructions"]
        assert "corpus:corpus-v1" in prompt["evidence_references"]
        assert "retrieval:ev-1" in prompt["evidence_references"]

    def test_optional_blocks_preserved(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        assert prompt["calculable"]["path_score"] == 0.2
        assert prompt["coherence_hints"]["hint"] == "bounded"


class TestPromptPolicyEnforcement:
    def test_clean_envelope_passes(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        assert enforce_prompt_policy(prompt) == []

    def test_forbidden_top_level_detected(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        prompt["input_text"] = "leak"
        violations = enforce_prompt_policy(prompt)
        assert any("input_text" in v for v in violations)

    def test_forbidden_nested_key_detected(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        prompt["engine_trace"]["hidden_reasoning"] = "secret"
        violations = enforce_prompt_policy(prompt)
        assert any("hidden_reasoning" in v for v in violations)

    def test_forbidden_phrase_detected(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        prompt["answer_instructions"] = "Use my internal reasoning as proof."
        violations = enforce_prompt_policy(prompt)
        assert any("forbidden_phrase" in v for v in violations)

    def test_raise_on_violation(self):
        prompt = build_prompt_envelope(_sample_input_envelope())
        prompt["chain_of_thought"] = "nope"
        with pytest.raises(PromptPolicyViolation) as exc:
            enforce_prompt_policy_or_raise(prompt)
        assert exc.value.violations
