# Engine semantic state (H_total) — core Hesperia; not TFP practical tests.
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from hesperia.nlp.semantic_state_update import (
    load_h_total,
    propagate_state,
    update_semantic_state,
    validate_h_total_symmetry_and_bounds,
)
from hesperia.nlp.invariant_activation import build_invariant_activation

_REPO_TESTS = Path(__file__).resolve().parents[1]
FIXTURE_H = _REPO_TESTS / "fixtures" / "semantic_dynamics" / "h_total_synthetic.json"


def _tiny_h_total() -> dict:
    return json.loads(FIXTURE_H.read_text(encoding="utf-8"))


def test_propagate_state_is_deterministic() -> None:
    h = _tiny_h_total()
    psi0: dict[str, float] = {}
    ev = {"B_A10_F10_001": 0.4, "B_A1_F10_001": 0.2}
    a, raw = propagate_state(psi0, ev, h, alpha=0.7, sat_k=1.2, prune_eps=0.03)
    b, _ = propagate_state(psi0, ev, h, alpha=0.7, sat_k=1.2, prune_eps=0.03)
    assert a == b
    l1 = sum(abs(v) for v in a.values())
    if sum(abs(v) for v in raw.values()) <= 1e-12:
        assert l1 <= 1e-9
    else:
        assert l1 <= 1.0 + 1e-5
        assert l1 > 1e-6


def test_validate_fixture_passes_symmetry_and_bounds() -> None:
    sym, bnd, detail = validate_h_total_symmetry_and_bounds(_tiny_h_total())
    assert sym is True
    assert bnd is True
    assert detail["concept_count"] == 2


def test_update_semantic_state_carries_psi() -> None:
    h = _tiny_h_total()
    ev1 = {"B_A10_F10_001": 0.5, "B_A1_F10_001": 0.0}
    psi1, aud1 = update_semantic_state(None, ev1, h, alpha=0.7)
    assert aud1["operator_applied"] is True
    ev2 = {"B_A10_F10_001": 0.0, "B_A1_F10_001": 0.5}
    psi2, _aud2 = update_semantic_state(psi1, ev2, h, alpha=0.7)
    psi_fresh, _ = update_semantic_state(None, ev2, h, alpha=0.7)
    assert psi2 != psi_fresh


def test_build_invariant_activation_with_semantic_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    from hesperia.engine import engine_signal_calibration as cal

    real = cal.load_engine_runtime_bundle()

    def _bundle() -> dict:
        out = copy.deepcopy(real)
        calib = dict(out["calibration"])
        calib["semantic_dynamics"] = {
            "operator_enabled": True,
            "h_total_relative_path": "semantic_dynamics/h_total_concepts.json",
            "alpha": 0.7,
            "sat_k": 1.2,
            "prune_eps": 0.03,
        }
        out["calibration"] = calib
        return out

    monkeypatch.setattr("hesperia.nlp.invariant_activation.load_engine_runtime_bundle", _bundle)
    monkeypatch.setattr(
        "hesperia.nlp.invariant_activation.load_h_total",
        lambda _path: _tiny_h_total(),
    )

    markers = [("B_A10_F10_001", 1.0)]
    af = {
        "B_A10_F10_001": ("A4", "F1"),
        "B_A1_F10_001": ("A7", "F1"),
    }
    act = build_invariant_activation(
        markers,
        token_count=4,
        concept_to_area_family=af,
        psi_prev=None,
        apply_semantic_state=True,
    )
    assert act.get("semantic_state", {}).get("operator_applied") is True
    assert "psi_concepts" in act
    assert act["invariant_activation"].get("semantic_state_operator_enabled") is True


def test_shipped_h_total_loads() -> None:
    p = (
        Path(__file__).resolve().parents[2]
        / "assets"
        / "data"
        / "engine_dynamics_v060"
        / "semantic_dynamics"
        / "h_total_concepts.json"
    )
    data = load_h_total(str(p))
    sym, bnd, _ = validate_h_total_symmetry_and_bounds(data)
    assert sym is True
    assert bnd is True
