# H070 sandbox apply tests.

from __future__ import annotations

from pathlib import Path

from runtime.h070_apply.executor import apply_update_edge_weight
from runtime.h070_apply.gates import run_gate_chain
from runtime.h070_apply.sandbox import create_sandbox


def test_sandbox_copy_records_parent_sha() -> None:
    parent = {"A->B": 0.5, "B->C": 0.2}
    sbx = create_sandbox(parent, parent_sha="abc123deadbeef")
    assert sbx["parent_sha"] == "abc123deadbeef"
    assert sbx["edges"] == parent
    sbx["edges"]["A->B"] = 0.9
    assert parent["A->B"] == 0.5


def test_apply_update_edge_weight_deterministic() -> None:
    sbx = create_sandbox({"AGGRESSION->SELF_REGULATION": 0.4}, parent_sha="sha1")
    prop = {
        "action": "update_edge_weight",
        "source": "AGGRESSION",
        "target": "SELF_REGULATION",
        "W_e_current": 0.4,
        "W_e_proposed": 0.72,
    }
    rep = apply_update_edge_weight(sbx, prop)
    assert rep["deterministic"] is True
    assert sbx["edges"]["AGGRESSION->SELF_REGULATION"] == 0.72


def test_gate_chain_happy_path(tmp_path: Path) -> None:
    parent = {"AGGRESSION->SELF_REGULATION": 0.0, "A->B": 0.5}
    prop = {
        "action": "update_edge_weight",
        "source": "AGGRESSION",
        "target": "SELF_REGULATION",
        "W_e_current": 0.0,
        "W_e_proposed": 0.6,
    }
    out = run_gate_chain(
        proposal=prop,
        parent_sha="parent-sha-001",
        parent_edges=parent,
        approval_id="approval-test-1",
        rollback_dir=tmp_path,
    )
    assert out["status"] == "applied"
    assert out["gates"]["G9"] == "PASS"
