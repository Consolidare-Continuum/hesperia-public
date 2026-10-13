# Tests for FPF-V7-13 — fpf-thinking-map governed calibration LLM calls.

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from sphere.calibration.llm_calibration import (
    PAYLOAD_PREFIX,
    build_governed_calibration_prompt,
    call_governed_calibration,
    calibration_evidence,
    step_calibration_gate,
)
from sphere.calibration.thinking_map import build_calibration_logic, build_calibration_map


DICT_A_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["segment_id", "concepts"],
    "properties": {
        "segment_id": {"type": "string"},
        "concepts": {"type": "array"},
    },
}


class TestCalibrationMap:
    def test_map_builds(self):
        sm = build_calibration_map()
        assert "hesperia_calibration" in sm.contexts
        logic = build_calibration_logic()
        assert logic is not None


class TestCalibrationGate:
    def test_dry_run_evidence(self):
        ev = calibration_evidence(dry_run=True)
        assert "dry_run" in ev
        assert "schema_bound" in ev

    def test_step_with_dry_run(self):
        out = step_calibration_gate(tool="dict_a", dry_run=True)
        assert out["tool"] == "dict_a"
        assert "kind" in out

    def test_step_blocks_without_provider(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            out = step_calibration_gate(tool="dict_a", dry_run=False)
            kind = str(out.get("kind") or "").lower()
            assert kind in ("collect_evidence", "denied", "abstain") or out.get("missing_evidence")


class TestGovernedPrompt:
    def test_prompt_is_json_envelope(self):
        outcome = {
            "kind": "continue",
            "llm_prompt_state": {"logic": {"facts": []}, "gate_status": {}},
        }
        prompt = build_governed_calibration_prompt(
            tool="dict_a",
            task_instructions="Calibrate concepts.",
            substrate={"segment_id": "s1", "text": "hello"},
            outcome=outcome,
        )
        assert prompt.startswith(PAYLOAD_PREFIX)
        payload = json.loads(prompt.split(PAYLOAD_PREFIX, 1)[1])
        assert payload["schema"] == "hesperia.calibration_prompt.v0_1"
        assert payload["tool"] == "dict_a"
        assert payload["substrate"]["segment_id"] == "s1"
        assert "input_text" not in payload


class TestCallGovernedCalibration:
    def test_dry_run_returns_empty_schema(self):
        result = call_governed_calibration(
            tool="dict_a",
            task_instructions="test",
            substrate={"segment_id": "seg-1"},
            schema=DICT_A_SCHEMA,
            cfg=None,
            dry_run=True,
        )
        assert result["segment_id"] == "seg-1"
        assert result["concepts"] == []

    def test_no_api_key_returns_empty_without_network(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = call_governed_calibration(
                tool="dict_a",
                task_instructions="test",
                substrate={"segment_id": "seg-2"},
                schema=DICT_A_SCHEMA,
                cfg=None,
                dry_run=False,
            )
        assert result["concepts"] == []
