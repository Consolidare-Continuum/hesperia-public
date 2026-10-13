# TASK_11 — system seal regression / completeness hooks.

from __future__ import annotations

from pathlib import Path

import pytest

from hesperia.system import system_seal as ss


@pytest.fixture
def repo() -> Path:
    return Path(__file__).resolve().parents[2]


def test_system_seal_gate_passes_with_physics_skipped(repo: Path, monkeypatch):
    """Completeness of checks without nested pytest (full suite runs in CI via run_system_seal)."""
    monkeypatch.delenv("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", raising=False)
    r = ss.run_system_seal_gate(repo, skip_physics_subprocess=True)
    assert r["status"] == "PASS", r.get("notes")
    assert all(r["checks"].values())


def test_system_seal_topology_hash_stable_across_runs(repo: Path, monkeypatch):
    monkeypatch.delenv("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", raising=False)
    a = ss.run_system_seal_gate(repo, skip_physics_subprocess=True)
    b = ss.run_system_seal_gate(repo, skip_physics_subprocess=True)
    assert a["hex_topology_sha256"] == b["hex_topology_sha256"]
    assert a["checks"].get("topology") and b["checks"].get("topology")


def test_system_seal_matrices_fail_when_dir_invalid(repo: Path, monkeypatch, tmp_path):
    monkeypatch.setenv("HESPERIA_PRODUCTION_MATRICES_DIR", str(tmp_path))
    monkeypatch.delenv("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", raising=False)
    try:
        r = ss.run_system_seal_gate(repo, skip_physics_subprocess=True)
        assert r["checks"]["matrices"] is False
    finally:
        monkeypatch.delenv("HESPERIA_PRODUCTION_MATRICES_DIR", raising=False)


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath("tests/physics_validation").is_dir(),
    reason="physics_validation missing",
)
def test_full_system_seal_including_physics_subprocess(repo: Path, monkeypatch):
    """Slower: nested pytest; run in CI or ``python -m tools.system_seal.run_system_seal``."""
    monkeypatch.delenv("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", raising=False)
    r = ss.run_system_seal_gate(repo, skip_physics_subprocess=False)
    assert r["status"] == "PASS", (r.get("checks"), r.get("notes"))
