# CHI-015 — TFP-FD gate + 34-param envelope + Ava smoke packs + C4 offline.

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hesperia.modules.tfp.field_dynamics_consumer import (
    C1_KEYS,
    C2_KEYS,
    C3_KEYS,
    C4_KEYS,
    C5_KEYS,
    TFP_FD_CONSUMER_ID,
    TFP_FD_ENV,
    build_tfp_fd_param_envelope,
    run_tfp_field_dynamics_artifact,
    run_tfp_hspr_offline_calib_job,
    tfp_field_dynamics_enabled,
)


@pytest.fixture(autouse=True)
def _clear_tfp_fd_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TFP_FD_ENV, raising=False)
    monkeypatch.delenv("HESPERIA_FIELD_DYNAMICS", raising=False)


def test_tfp_fd_gate_default_off() -> None:
    assert tfp_field_dynamics_enabled() is False


def test_run_skipped_when_gate_off(tmp_path: Path) -> None:
    out = run_tfp_field_dynamics_artifact("hello", tmp_path, tmp_path)
    assert out["_skipped"] is True
    assert "tfp_fd_envelope" not in out


def test_envelope_has_all_34_keys() -> None:
    env = build_tfp_fd_param_envelope()
    assert env["key_counts"]["total_34"] == 34
    packs = env["packs"]
    for k in C1_KEYS:
        assert k in packs["c1_phase3"]
    for k in C2_KEYS:
        assert k in packs["c2_phase4"]
    for k in C3_KEYS:
        assert k in packs["c3_xi"]
    for k in C4_KEYS:
        assert k in packs["c4_hspr_offline"]
    assert packs["c4_hspr_offline"]["runtime_score"] is False
    for k in C5_KEYS:
        assert k in packs["c5_semantic_field"]


def test_gate_on_envelope_no_full_dynamics_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    out = run_tfp_field_dynamics_artifact("hello", tmp_path, tmp_path)
    assert out["tfp_field_dynamics"] is True
    assert out["tfp_fd_envelope"]["key_counts"]["total_34"] == 34
    assert os.environ.get("HESPERIA_FIELD_DYNAMICS") in (None, "")


def test_c1_pack_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    packs = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)["tfp_fd_envelope"]["packs"]
    assert set(C1_KEYS) <= set(packs["c1_phase3"])


def test_c2_pack_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    packs = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)["tfp_fd_envelope"]["packs"]
    assert set(C2_KEYS) <= set(packs["c2_phase4"])


def test_c3_pack_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    packs = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)["tfp_fd_envelope"]["packs"]
    assert set(C3_KEYS) <= set(packs["c3_xi"])


def test_c5_pack_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    packs = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)["tfp_fd_envelope"]["packs"]
    assert set(C5_KEYS) <= set(packs["c5_semantic_field"])


def test_e2e_all_packs_gate_on(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(TFP_FD_ENV, "1")
    out = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)
    assert out["tfp_fd_envelope"]["key_counts"]["total_34"] == 34
    monkeypatch.delenv(TFP_FD_ENV, raising=False)
    off = run_tfp_field_dynamics_artifact("x", tmp_path, tmp_path)
    assert off.get("_skipped") is True


def test_c4_offline_job_writes_report(tmp_path: Path) -> None:
    rep = run_tfp_hspr_offline_calib_job(tmp_path)
    assert rep["runtime_score"] is False
    assert Path(rep["path"]).is_file()
    for k in C4_KEYS:
        assert k in rep["weights"]


def test_default_interpret_env_clean() -> None:
    assert tfp_field_dynamics_enabled() is False
    assert os.environ.get(TFP_FD_ENV) in (None, "")
    assert os.environ.get("HESPERIA_FIELD_DYNAMICS") in (None, "")
    assert TFP_FD_CONSUMER_ID
