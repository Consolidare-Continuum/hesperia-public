# HESPERIA 0.7.0 gate chain G1–G9.
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from runtime.h070_apply.audit import append_apply_audit
from runtime.h070_apply.executor import ALLOWED_ACTIONS
from runtime.h070_apply.ledger import record_applied
from runtime.h070_apply.replay import run_replay_benchmarks
from runtime.h070_apply.sandbox import graph_content_hash
from runtime.irc_teacher.teacher_v063 import validate_teacher_response_v063

_PROPOSAL_META_KEYS = frozenset({"id", "proposal_id", "evidence_ids"})
_PROPOSAL_STRING_KEYS = frozenset({"action", "source", "target", "type", "concept_id", "field"})


def _proposal_for_validation(proposal: dict[str, Any]) -> dict[str, Any]:
    """Strip H070 metadata before v063 schema validation."""
    out: dict[str, Any] = {}
    for k, v in proposal.items():
        if k in _PROPOSAL_META_KEYS:
            continue
        if isinstance(v, str) and k not in _PROPOSAL_STRING_KEYS:
            continue
        out[k] = v
    return out


def score_improvement(baseline: dict[str, float], after: dict[str, float]) -> dict[str, Any]:
    """G5 stub: primary metric = fewer zero-weight edges."""
    b_zeros = sum(1 for v in baseline.values() if float(v) == 0.0)
    a_zeros = sum(1 for v in after.values() if float(v) == 0.0)
    return {
        "missing_bridge_delta": b_zeros - a_zeros,
        "improved": (b_zeros - a_zeros) > 0,
    }


def score_damage(baseline_incidents: int, after_incidents: int) -> dict[str, Any]:
    """G6 stub."""
    delta = after_incidents - baseline_incidents
    return {"incident_count_delta": delta, "damage_ok": delta <= 0}


def run_gate_chain(
    *,
    proposal: dict[str, Any],
    parent_sha: str,
    parent_edges: dict[str, float],
    baseline_incidents: int = 0,
    after_incidents: int = 0,
    approval_id: str | None = None,
    rollback_dir: Path | None = None,
) -> dict[str, Any]:
    """Run G1–G9 sequentially; halt on first fail."""
    results: dict[str, Any] = {"gates": {}, "status": "pending"}
    try:
        prop_v = _proposal_for_validation(proposal)
        validate_teacher_response_v063(
            {"schema": "hesperia.teacher_response.v063", "lang": "ru", "proposals": [prop_v]}
        )
        if prop_v.get("action") not in ALLOWED_ACTIONS:
            raise ValueError("G1 allowlist fail")
        results["gates"]["G1"] = "PASS"
        from runtime.h070_apply.executor import apply_update_edge_weight
        from runtime.h070_apply.sandbox import create_sandbox

        sandbox = create_sandbox(parent_edges, parent_sha=parent_sha)
        results["gates"]["G2"] = "PASS"
        apply_report = apply_update_edge_weight(sandbox, prop_v)
        if not apply_report.get("deterministic"):
            raise ValueError("G3 nondeterministic diff")
        results["gates"]["G3"] = "PASS"
        results["apply_report"] = apply_report
        replay = run_replay_benchmarks()
        if not replay.get("pass"):
            raise ValueError("G4 replay benchmark fail")
        results["replay"] = replay
        results["gates"]["G4"] = "PASS"
        imp = score_improvement(parent_edges, sandbox["edges"])
        if not imp.get("improved"):
            raise ValueError("G5 improvement fail")
        results["improvement"] = imp
        results["gates"]["G5"] = "PASS"
        dmg = score_damage(baseline_incidents, after_incidents)
        if not dmg.get("damage_ok"):
            raise ValueError("G6 damage fail")
        results["damage"] = dmg
        results["gates"]["G6"] = "PASS"
        if not approval_id:
            raise ValueError("G7 approval missing")
        results["approval_id"] = approval_id
        results["gates"]["G7"] = "PASS"
        rb_dir = rollback_dir or Path("/tmp/hesperia-h070-rollback")
        rb_dir.mkdir(parents=True, exist_ok=True)
        artifact = rb_dir / f"{sandbox['sandbox_id']}.json"
        artifact.write_text(
            json.dumps({"parent_sha": parent_sha, "edges": parent_edges}, indent=2),
            encoding="utf-8",
        )
        results["rollback_artifact"] = str(artifact)
        results["gates"]["G8"] = "PASS"
        canonical_hash = graph_content_hash(sandbox["edges"])
        results["canonical_write"] = {
            "edges": sandbox["edges"],
            "content_hash": canonical_hash,
            "applied_ts": int(time.time()),
        }
        proposal_id = str(proposal.get("proposal_id") or proposal.get("id") or sandbox["sandbox_id"])
        ledger_row = record_applied(
            proposal_id=proposal_id,
            canonical_hash=canonical_hash,
            approval_id=approval_id,
        )
        results["ledger"] = ledger_row
        append_apply_audit(
            {
                "proposal_id": proposal_id,
                "gates": results["gates"],
                "status": "applied",
                "rollback_artifact": results.get("rollback_artifact"),
                "canonical_hash": canonical_hash,
            }
        )
        results["gates"]["G9"] = "PASS"
        results["status"] = "applied"
    except Exception as exc:
        results["status"] = "rejected"
        results["error"] = str(exc)
    return results
