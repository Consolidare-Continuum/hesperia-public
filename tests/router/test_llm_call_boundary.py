# Tests for HSR-V7-D-24/25: LLM call timeout, retry, and JSONL logging.

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sphere.router.llm_interpret import (
    LlmCallTimeout,
    LlmInterpretConfig,
    MockLlmClient,
    interpret_router_envelope,
)


def _envelope() -> dict:
    return {
        "schema": "hesperia.router_input_envelope.v0_1",
        "router_version": "v7-router-0.1",
        "input_hash": "b" * 64,
        "input_text": "ignored in prompt path",
        "engine_trace": {"dominant_area_id": "T1"},
        "logic_mapping": {},
        "retrieval_context": {},
        "relation_context": {},
        "policy_block": {},
        "corpus_snapshot_id": "corpus-unset",
        "policy_snapshot_id": "HSR-V7-01",
        "router_fingerprint": "c" * 64,
    }


class TestLlmCallBoundary:
    def test_prompt_envelope_attached(self):
        result = interpret_router_envelope(
            _envelope(),
            cfg=LlmInterpretConfig(provider="mock"),
            client=MockLlmClient(),
        )
        assert result["call_status"] == "ok"
        assert result["prompt_envelope"]["schema"] == "hesperia.router_prompt_envelope.v0_1"
        assert "input_text" not in result["prompt_envelope"]
        assert result["output_hash"]

    def test_timeout_returns_empty_narrative_block(self):
        slow = MockLlmClient(delay_seconds=2.0)
        result = interpret_router_envelope(
            _envelope(),
            cfg=LlmInterpretConfig(provider="mock", timeout_seconds=0.1, max_retries=0),
            client=slow,
        )
        assert result["call_status"] == "failed"
        assert result["narrative"]["summary"] == ""
        assert result["output_hash"]

    def test_retry_then_success(self):
        flaky = MockLlmClient(fail_times=1)
        result = interpret_router_envelope(
            _envelope(),
            cfg=LlmInterpretConfig(provider="mock", timeout_seconds=5.0, max_retries=1),
            client=flaky,
        )
        assert result["call_status"] == "ok"
        assert result["attempt"] == 2

    def test_policy_violation_blocks_call(self):
        bad = _envelope()
        bad["policy_block"] = {"forbidden_actions": ["ok"], "hidden_reasoning": "x"}
        result = interpret_router_envelope(
            bad,
            cfg=LlmInterpretConfig(provider="mock"),
            client=MockLlmClient(),
        )
        assert result["call_status"] == "policy_violation"
        assert result["narrative"]["summary"] == ""

    def test_empty_llm_result_audits_block(self):
        from sphere.router.audit import audit_router_output

        failed = interpret_router_envelope(
            _envelope(),
            cfg=LlmInterpretConfig(provider="mock", timeout_seconds=0.05, max_retries=0),
            client=MockLlmClient(delay_seconds=1.0),
        )
        bundle = audit_router_output(_envelope(), failed)
        assert bundle["router_decision"]["decision"] == "BLOCK"
        assert "EMPTY_OUTPUT" in bundle["router_decision"]["decision_reasons"]


class TestLlmCallLogging:
    def test_jsonl_log_written(self, tmp_path: Path):
        log_file = tmp_path / "llm_calls.jsonl"
        with patch.dict(os.environ, {"HESPERIA_LLM_CALL_LOG": str(log_file)}):
            interpret_router_envelope(
                _envelope(),
                cfg=LlmInterpretConfig(provider="mock"),
                client=MockLlmClient(),
            )
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["input_hash"] == "b" * 64
        assert record["provider"] == "mock"
        assert record["status"] == "ok"
        assert "latency_ms" in record
