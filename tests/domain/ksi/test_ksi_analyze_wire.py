# HESPERIA — KSI wire into sealed /analyze (HES-MATH-BEHAV-32).
from __future__ import annotations

from typing import Any

import pytest

from core.domain.ksi.expected_j import IncomingEdge
from core.domain.ksi.pipeline import (
    attach_ksi_to_engine_result,
    run_ksi_inspect,
    run_ksi_inspect_from_engine,
)
from sphere.router.engine_analyze_bridge import build_engine_analyze_from_raw


def _raw_min() -> dict[str, Any]:
    return {
        "multiscale_signals": {
            "family_activation_vector": [0.0, 0.9, 0.1] + [0.0] * 285,
            "hspr_index": 0.42,
            "contradiction_pressure": 0.11,
            "propagation_strength": 0.55,
        },
        "diagnostics": {
            "interpretability_trace": {
                "marker_concept_sample": [
                    {
                        "token": "shame",
                        "concept_id": "SHAME",
                        "linked_family": 1,
                        "concept_index": 1,
                    },
                    {
                        "token": "failure",
                        "concept_id": "FAILURE",
                        "linked_family": 1,
                        "concept_index": 1,
                    },
                ]
            }
        },
    }


def test_attach_ksi_noop_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_KSI_ENABLED", raising=False)
    engine = {"trace": [{"concept_id": "SHAME", "activation": 0.8, "area_id": "A1", "family_id": "f"}]}
    out = attach_ksi_to_engine_result(dict(engine))
    assert "ksi" not in out


def test_attach_ksi_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_KSI_ENABLED", "1")
    monkeypatch.setenv("HESPERIA_KSI_PHI_TRACE", "0")
    monkeypatch.setenv("HESPERIA_KSI_TEACHER_PACKET", "1")
    engine = {
        "trace": [
            {"concept_id": "SHAME", "activation": 0.3, "area_id": "A1", "family_id": "f0"},
            {"concept_id": "FAILURE", "activation": 0.85, "area_id": "A1", "family_id": "f0"},
        ],
        "ksi_edges": [
            {"source": "FAILURE", "target": "SHAME", "relation_type": "activates", "w_e": 0.8},
        ],
    }
    out = attach_ksi_to_engine_result(dict(engine))
    assert "ksi" in out
    ksi = out["ksi"]
    assert ksi["version"] == "0.1"
    assert "SHAME" in ksi["concepts"]
    assert ksi["concepts"]["SHAME"]["expected"] > 0.0
    assert "teacher_packet" in ksi
    assert ksi["teacher_packet"]["apply_allowed"] is False
    assert ksi["teacher_packet"]["mode"] == "inspect_only"
    assert ksi["teacher_packet"]["apply_gate"] == "blocked_until_0.7.0"


def test_phi_trace_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_KSI_ENABLED", "1")
    monkeypatch.setenv("HESPERIA_KSI_PHI_TRACE", "1")
    monkeypatch.setenv("HESPERIA_KSI_TEACHER_PACKET", "0")
    block = run_ksi_inspect(
        activations={"FAILURE": 0.9, "SHAME": 0.2},
        incoming_edges=[
            IncomingEdge(source="FAILURE", target="SHAME", relation_type="activates", w_e=0.7),
        ],
        include_phi_trace=True,
        include_teacher_packet=False,
    )
    assert block["phi_trace"]
    assert "FAILURE→SHAME" in block["phi_trace"]


def test_sealed_analyze_envelope_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_KSI_ENABLED", raising=False)
    out = build_engine_analyze_from_raw(_raw_min())
    assert out["contract_version"] == "v1.0"
    assert "ksi" not in out
    assert out["trace"]


def test_sealed_analyze_envelope_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_KSI_ENABLED", "1")
    monkeypatch.setenv("HESPERIA_KSI_TEACHER_PACKET", "0")
    out = build_engine_analyze_from_raw(_raw_min())
    assert "ksi" in out
    assert out["ksi"]["version"] == "0.1"
    # Trace concepts become Observed_j even without edges.
    assert out["ksi"]["concepts"]


def test_run_ksi_inspect_from_engine_empty() -> None:
    assert run_ksi_inspect_from_engine({})["version"] == "0.1"
    assert run_ksi_inspect_from_engine(None)["version"] == "0.1"


def test_env_guard_lists_live_ksi_flags() -> None:
    from runtime.shipping.env_guard import ALLOWED_HESPERIA_ENV

    required = {
        "HESPERIA_KSI_ENABLED",
        "HESPERIA_KSI_CONFIG",
        "HESPERIA_KSI_PHI_TRACE",
        "HESPERIA_KSI_LLM_TEACHER",
        "HESPERIA_KSI_TEACHER_MODEL",
        "HESPERIA_KSI_SANDBOX_FIXTURES",
        "HESPERIA_KSI_TAU",
        "HESPERIA_KSI_TAU_BRIDGE",
        "HESPERIA_KSI_TAU_TEACHER",
        "HESPERIA_KSI_TEACHER_INSPECT_ONLY",
        "HESPERIA_KSI_TEACHER_PACKET",
    }
    missing = required - set(ALLOWED_HESPERIA_ENV)
    assert not missing, f"env_guard missing KSI flags: {sorted(missing)}"


def test_hybrid_retriever_wires_ksi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_KSI_ENABLED", "1")
    monkeypatch.setenv("HESPERIA_KSI_TEACHER_PACKET", "0")
    monkeypatch.setenv("HESPERIA_ENGINE_ENABLED", "0")

    from runtime.irc_teacher.analyze_adapter import HybridRetrieveInput, retrieve

    # Engine disabled → local None; attach still no-ops on None path.
    # Inject engine_result via monkeypatch of _call_engine.
    def _fake_call(_query: str, timeout_s: float = 8.0) -> dict[str, Any]:
        return {
            "trace": [
                {"concept_id": "A", "activation": 0.9, "area_id": "A1", "family_id": "f0"},
                {"concept_id": "B", "activation": 0.2, "area_id": "A1", "family_id": "f0"},
            ],
            "ksi_edges": [{"source": "A", "target": "B", "relation_type": "activates", "w_e": 0.6}],
        }

    monkeypatch.setattr("runtime.irc_teacher.analyze_adapter._call_engine", _fake_call)
    out = retrieve(HybridRetrieveInput(query="test"))
    assert out.engine_result is not None
    assert out.engine_result.get("ksi")
    assert out.context_package and out.context_package.get("ksi")
