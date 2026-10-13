# H070 gold tests — sandbox apply approve / reject / rollback.
from __future__ import annotations

from pathlib import Path

import pytest

from runtime.h070_apply.gates import run_gate_chain
from runtime.h070_apply.replay import load_replay_benchmarks, run_replay_benchmarks


def test_replay_fixture_has_ten_plus_statements() -> None:
    items = load_replay_benchmarks()
    assert len(items) >= 10


def test_replay_benchmarks_pass() -> None:
    out = run_replay_benchmarks()
    assert out["pass"] is True
    assert out["ok_count"] >= 10


def test_gold_sandbox_apply_approve_canonical_write(tmp_path: Path) -> None:
    parent = {"AGGRESSION->SELF_REGULATION": 0.0, "A->B": 0.5}
    prop = {
        "id": "gold-approve-1",
        "action": "update_edge_weight",
        "source": "AGGRESSION",
        "target": "SELF_REGULATION",
        "W_e_current": 0.0,
        "W_e_proposed": 0.6,
        "evidence_ids": ["ev-gold-001"],
    }
    out = run_gate_chain(
        proposal=prop,
        parent_sha="parent-sha-gold",
        parent_edges=parent,
        approval_id="approval-gold-1",
        rollback_dir=tmp_path,
    )
    assert out["status"] == "applied"
    assert out["ledger"]["applied"] == 1
    assert Path(out["rollback_artifact"]).is_file()


def test_gold_damage_reject_sandbox_discard(tmp_path: Path) -> None:
    parent = {"AGGRESSION->SELF_REGULATION": 0.0}
    prop = {
        "action": "update_edge_weight",
        "source": "AGGRESSION",
        "target": "SELF_REGULATION",
        "W_e_current": 0.0,
        "W_e_proposed": 0.1,
    }
    out = run_gate_chain(
        proposal=prop,
        parent_sha="sha",
        parent_edges=parent,
        baseline_incidents=0,
        after_incidents=3,
        approval_id="approval-x",
        rollback_dir=tmp_path,
    )
    assert out["status"] == "rejected"
    assert "G6" not in out.get("gates", {}) or out["gates"].get("G6") != "PASS"


def test_gold_rollback_restore_dry_run(tmp_path: Path) -> None:
    parent = {"AGGRESSION->SELF_REGULATION": 0.0, "X->Y": 0.3}
    prop = {
        "action": "update_edge_weight",
        "source": "AGGRESSION",
        "target": "SELF_REGULATION",
        "W_e_current": 0.0,
        "W_e_proposed": 0.55,
    }
    out = run_gate_chain(
        proposal=prop,
        parent_sha="rollback-parent",
        parent_edges=parent,
        approval_id="approval-rb",
        rollback_dir=tmp_path,
    )
    assert out["status"] == "applied"
    artifact = Path(out["rollback_artifact"])
    assert artifact.is_file()
    import json

    snap = json.loads(artifact.read_text(encoding="utf-8"))
    assert snap["parent_sha"] == "rollback-parent"
    assert snap["edges"] == parent
