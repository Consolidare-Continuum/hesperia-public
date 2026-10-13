# CHI-016 — first-class interpret: Layer-9, hspr_index honesty, opt-in TFP-FD.

from __future__ import annotations

import os

import pytest

from hesperia.modules.tfp.field_dynamics_consumer import TFP_FD_ENV
from runtime.services.product_interpret_service import run_product_interpret
from sphere.logic import evaluate_rules


@pytest.fixture(autouse=True)
def _clear_tfp_fd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TFP_FD_ENV, raising=False)


def test_interpret_layer9_and_hspr_always() -> None:
    r = run_product_interpret("CHI-016 layer9 smoke text.", mode="deterministic")
    assert "layer9_logic" in r
    assert r["layer9_logic"]["source"] == "logic_rules.yaml"
    assert "facts" in r["layer9_logic"]
    assert "hspr_index" in r
    assert r.get("hspr_index_note", "").startswith("live_system")
    assert "tfp_field_dynamics" not in r or r.get("tfp_field_dynamics", {}).get("attached") is not True


def test_interpret_gold_unchanged_without_fd_flag() -> None:
    a = run_product_interpret("gold baseline interpret.", mode="deterministic")
    b = run_product_interpret(
        "gold baseline interpret.",
        mode="deterministic",
        include_tfp_field_dynamics=False,
    )
    assert a["schema"] == b["schema"]
    assert "tfp_field_dynamics" not in a
    assert "tfp_field_dynamics" not in b


def test_interpret_fd_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    r = run_product_interpret(
        "fd request without env.",
        mode="deterministic",
        include_tfp_field_dynamics=True,
    )
    assert r["tfp_field_dynamics"]["attached"] is False
    assert "env_gate_off" in r["tfp_field_dynamics"]["reason"]


def test_interpret_fd_on_with_flag_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    r = run_product_interpret(
        "fd request with env.",
        mode="deterministic",
        include_tfp_field_dynamics=True,
    )
    assert r["tfp_field_dynamics"]["attached"] is True
    assert r["tfp_field_dynamics"]["envelope"]["key_counts"]["total_34"] == 34


def test_rule_006_low_diversity_in_logic_rules() -> None:
    out = evaluate_rules({"unique_areas": 1, "entropy": 0.9, "governance_area": 0.0,
                          "curvature": 0.0, "coverage": 0.9, "stability_index": 0.9})
    codes = {t.get("diagnostic_code") for t in out["triggered_rules"]}
    assert "LOW_DIVERSITY" in codes


def test_activation_getters_sot() -> None:
    from hesperia.engine.calibration.activation_calibration import (
        get_activation_threshold,
        get_area_active_threshold,
    )
    from hesperia.engine.kme import clinical_bridge as cb

    assert cb.ACTIVATION_THRESHOLD == get_activation_threshold()
    assert cb.AREA_ACTIVE_THRESHOLD == get_area_active_threshold()
