# HESPERIA — KAM apply-gate lens + env flags / env_guard
from __future__ import annotations

import pytest

from sphere.kam.apply_gate import inspect_apply_gate
from sphere.kam.flags import kam_enabled
from sphere.kam.pipeline import attach_kam_to_engine_result, run_kam_inspect


class TestFlags:
    def test_default_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HESPERIA_KAM_ENABLED", raising=False)
        assert kam_enabled() is False

    def test_enabled_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HESPERIA_KAM_ENABLED", "1")
        assert kam_enabled() is True


class TestEnvGuard:
    def test_env_guard_lists_kam_flags(self) -> None:
        from runtime.shipping.env_guard import ALLOWED_HESPERIA_ENV

        required = {
            "HESPERIA_KAM_ENABLED",
            "HESPERIA_KAM_BOUNDS",
            "HESPERIA_KAM_INSPECT_ONLY",
        }
        missing = required - set(ALLOWED_HESPERIA_ENV)
        assert not missing, f"env_guard missing KAM flags: {sorted(missing)}"


class TestApplyGateLens:
    def test_inspect_only_pre_070(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HESPERIA_KAM_INSPECT_ONLY", "1")
        lens = inspect_apply_gate(
            {
                "baseline_id": "sha256:test",
                "kam_verdict": "structurally_robust",
            },
            nash_repair_stability_ok=True,
        )
        assert lens.mutates_graph is False
        assert lens.status == "inspect_only"
        assert lens.allow_sandbox_apply_candidate is False

    def test_hard_block_fragile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HESPERIA_KAM_INSPECT_ONLY", "0")
        lens = inspect_apply_gate(
            {"baseline_id": "sha256:x", "kam_verdict": "fragile_trajectory"},
            nash_repair_stability_ok=True,
        )
        assert lens.status == "hard_block"
        assert lens.allow_sandbox_apply_candidate is False
        assert lens.mutates_graph is False

    def test_insufficient_baseline_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HESPERIA_KAM_INSPECT_ONLY", "0")
        lens = inspect_apply_gate(
            {"baseline_id": "sha256:x", "kam_verdict": "insufficient_baseline"},
        )
        assert lens.status == "hard_block"

    def test_allow_candidate_when_not_inspect_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HESPERIA_KAM_INSPECT_ONLY", "0")
        lens = inspect_apply_gate(
            {"baseline_id": "sha256:x", "kam_verdict": "structurally_robust"},
            nash_repair_stability_ok=True,
        )
        assert lens.status == "allow_candidate"
        assert lens.allow_sandbox_apply_candidate is True
        assert lens.mutates_graph is False


class TestPipeline:
    def test_disabled_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HESPERIA_KAM_ENABLED", raising=False)
        out = run_kam_inspect({"concepts_activated": [{"id": "c", "weight": 1.0}]})
        assert out["enabled"] is False
        er: dict = {"trace": []}
        attach_kam_to_engine_result(er)
        assert "kam_stability" not in er

    def test_enabled_attach_inspect_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HESPERIA_KAM_ENABLED", "1")
        monkeypatch.setenv("HESPERIA_KAM_INSPECT_ONLY", "1")
        bundle = {
            "concepts_activated": [
                {"id": "A", "weight": 0.9},
                {"id": "B", "weight": 0.5},
            ],
            "families_activated": [{"id": "F1", "weight": 0.7}],
            "areas_activated": [{"id": "A1", "weight": 0.8}],
            "propagation_trace": [{"rule_tag": "t1"}, {"rule_tag": "t2"}],
            "contradiction_pressure": 0.1,
            "propagation_corridors": {
                "corridor_edges": [{"id": "e1", "mass": 0.5}, {"id": "e2", "mass": 0.3}]
            },
        }
        block = run_kam_inspect(bundle)
        assert block["enabled"] is True
        assert block["not_a_theorem"] is True
        report = block["report"]
        assert report["schema"] == "hesperia.kam_perturbation_report.v01"
        assert block["apply_gate_lens"]["mutates_graph"] is False
        assert block["apply_gate_lens"]["status"] == "inspect_only"

        er: dict = dict(bundle)
        attach_kam_to_engine_result(er)
        assert "kam_stability" in er
        assert er["kam_stability"]["schema"] == "hesperia.kam_perturbation_report.v01"
