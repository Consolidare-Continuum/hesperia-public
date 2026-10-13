# Tests for HSR-V7-D-43..46: router governance modes (observe/warn/strict).

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from runtime.services.product_interpret_service import (
    _apply_router_governance,
    _router_mode,
)


class TestRouterMode:
    def test_default_observe(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HESPERIA_ROUTER_MODE", None)
            assert _router_mode() == "observe"

    def test_env_warn(self):
        with patch.dict(os.environ, {"HESPERIA_ROUTER_MODE": "warn"}):
            assert _router_mode() == "warn"

    def test_env_strict(self):
        with patch.dict(os.environ, {"HESPERIA_ROUTER_MODE": "strict"}):
            assert _router_mode() == "strict"

    def test_invalid_falls_back_observe(self):
        with patch.dict(os.environ, {"HESPERIA_ROUTER_MODE": "yolo"}):
            assert _router_mode() == "observe"


def _make_result(decision: str = "ALLOW") -> dict:
    return {
        "schema": "hesperia.product_interpret.v0_1",
        "mode": "llm",
        "router_envelope": {"router_fingerprint": "abc123"},
        "interpretation": {"mode": "deterministic", "structural_summary": "test"},
        "llm": {"provider": "mock", "narrative": {"summary": "test output"}},
        "router_decision": {"decision": decision, "decision_reasons": []},
        "decision": decision,
    }


class TestObserveMode:
    def test_allow_passes_through(self):
        out = _apply_router_governance(_make_result("ALLOW"), "observe")
        assert out["router_mode"] == "observe"
        assert "llm" in out
        assert "governance_warning" not in out
        assert "governance_block" not in out

    def test_block_passes_through_in_observe(self):
        out = _apply_router_governance(_make_result("BLOCK"), "observe")
        assert "llm" in out
        assert "governance_block" not in out


class TestWarnMode:
    def test_allow_no_warning(self):
        out = _apply_router_governance(_make_result("ALLOW"), "warn")
        assert "governance_warning" not in out

    def test_warn_adds_warning(self):
        out = _apply_router_governance(_make_result("WARN"), "warn")
        assert "governance_warning" in out
        assert "WARN" in out["governance_warning"]
        assert "llm" in out

    def test_block_adds_warning(self):
        out = _apply_router_governance(_make_result("BLOCK"), "warn")
        assert "governance_warning" in out
        assert "llm" in out

    def test_review_adds_warning(self):
        out = _apply_router_governance(_make_result("REVIEW_REQUIRED"), "warn")
        assert "governance_warning" in out


class TestStrictMode:
    def test_allow_passes_through(self):
        out = _apply_router_governance(_make_result("ALLOW"), "strict")
        assert "llm" in out
        assert "governance_block" not in out

    def test_warn_passes_through_in_strict(self):
        out = _apply_router_governance(_make_result("WARN"), "strict")
        assert "llm" in out
        assert "governance_block" not in out

    def test_block_suppresses_llm(self):
        out = _apply_router_governance(_make_result("BLOCK"), "strict")
        assert "llm" not in out
        assert out["governance_block"] is True
        assert out["interpretation"]["mode"] == "blocked"
        assert "BLOCK" in out["interpretation"]["structural_summary"]

    def test_review_required_suppresses_llm(self):
        out = _apply_router_governance(_make_result("REVIEW_REQUIRED"), "strict")
        assert "llm" not in out
        assert out["governance_block"] is True

    def test_blocked_preserves_fingerprint(self):
        out = _apply_router_governance(_make_result("BLOCK"), "strict")
        assert out["interpretation"]["router_fingerprint"] == "abc123"


class TestNoBypass:
    """D-46: verify no code path surfaces raw LLM text when decision is BLOCK in strict mode."""

    def test_strict_block_has_no_raw_llm_keys(self):
        out = _apply_router_governance(_make_result("BLOCK"), "strict")
        assert "llm" not in out
        interp = out.get("interpretation", {})
        assert "narrative" not in interp
        assert interp.get("mode") == "blocked"
