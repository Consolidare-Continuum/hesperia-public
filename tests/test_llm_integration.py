# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# See LEGAL_NOTICE.md for full terms.

"""Tests for sphere/fpf_bridge/llm_integration — deterministic via MockLlmClient."""

from __future__ import annotations

import copy
import json

import pytest

from sphere.fpf_bridge.bridge import bridge_to_llm_prompt
from sphere.fpf_bridge.llm_integration import (
    LlmInterpretConfig,
    MockLlmClient,
    PAYLOAD_PREFIX,
    STRUCTURAL_NARRATIVE_SCHEMA,
    build_interpretation_messages,
    interpret_prompt_state,
    interpret_structural_state,
    mock_narrative_from_prompt,
)
from tests.fixtures.mock_pipeline_result import make_pipeline_result


class TestBuildMessages:
    def test_messages_include_system_and_user(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        messages = build_interpretation_messages(prompt)
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "structural" in messages[1]["content"].lower()

    def test_user_payload_is_valid_json(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        messages = build_interpretation_messages(prompt)
        user = messages[1]["content"]
        assert PAYLOAD_PREFIX in user
        parsed = json.loads(user.split(PAYLOAD_PREFIX, 1)[1].strip())
        assert "initial_outcome" in parsed


class TestMockInterpretation:
    def test_interpret_structural_state_envelope(self):
        result = make_pipeline_result()
        cfg = LlmInterpretConfig(provider="mock")
        envelope = interpret_structural_state(
            result,
            cfg=cfg,
            client=MockLlmClient(),
        )
        assert envelope["provider"] == "mock"
        assert "prompt_state" in envelope
        assert "narrative" in envelope
        narrative = envelope["narrative"]
        assert narrative["structural_state"] == "focused_dominant"
        assert narrative["confidence"] in ("low", "medium", "high")
        assert isinstance(narrative["recommended_actions"], list)

    def test_interpret_prompt_state_idempotent_with_mock(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        cfg = LlmInterpretConfig(provider="mock")
        a = interpret_prompt_state(prompt, cfg=cfg, client=MockLlmClient())
        b = interpret_prompt_state(prompt, cfg=cfg, client=MockLlmClient())
        assert a["narrative"] == b["narrative"]

    def test_mock_narrative_schema_keys(self):
        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        narrative = mock_narrative_from_prompt(prompt)
        for key in STRUCTURAL_NARRATIVE_SCHEMA["required"]:
            assert key in narrative

    def test_bridge_input_not_mutated(self):
        result = make_pipeline_result()
        before = copy.deepcopy(result)
        interpret_structural_state(result, cfg=LlmInterpretConfig(provider="mock"), client=MockLlmClient())
        assert result == before

    @pytest.mark.parametrize("structural_state", [
        "focused_dominant",
        "tension_elevated",
        "distributed_balanced",
    ])
    def test_all_structural_states_mock(self, structural_state: str):
        result = make_pipeline_result(
            interpretation_metrics={"structural_state": structural_state},
        )
        envelope = interpret_structural_state(
            result,
            cfg=LlmInterpretConfig(provider="mock"),
            client=MockLlmClient(),
        )
        assert envelope["narrative"]["structural_state"] == structural_state


class TestProviderErrors:
    def test_openai_without_key_raises(self):
        import os

        result = make_pipeline_result()
        prompt = bridge_to_llm_prompt(result)
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                interpret_prompt_state(prompt, cfg=LlmInterpretConfig(provider="openai"))
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old
