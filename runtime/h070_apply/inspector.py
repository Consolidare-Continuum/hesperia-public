# H070 Inspector Pane 2 — gate state machine view model (no LLM prose).
from __future__ import annotations

from typing import Any

PANE2_STATES = (
    "pending",
    "sandbox",
    "replay",
    "scored",
    "awaiting_approval",
    "applied",
    "rejected",
)


def _gate_index(gates: dict[str, str], gate: str) -> int:
    order = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9")
    if gate not in order:
        return -1
    idx = order.index(gate)
    for g in order[: idx + 1]:
        if gates.get(g) != "PASS":
            return order.index(g)
    return idx + 1


def derive_pane2_phase(gates: dict[str, str], status: str) -> str:
    """Map gate progress to canonical Pane 2 state machine."""
    if status == "rejected":
        return "rejected"
    if gates.get("G9") == "PASS" and status == "applied":
        return "applied"
    if gates.get("G7") == "PASS":
        return "awaiting_approval" if status != "applied" else "applied"
    if gates.get("G6") == "PASS" or gates.get("G5") == "PASS":
        return "scored"
    if gates.get("G4") == "PASS":
        return "replay"
    if gates.get("G2") == "PASS" or gates.get("G3") == "PASS":
        return "sandbox"
    return "pending"


def build_state_timeline(phase: str) -> list[dict[str, str]]:
    """Stepper for template — each step active|done|rejected|upcoming."""
    linear = list(PANE2_STATES[:-1])  # exclude rejected from linear path
    if phase == "rejected":
        out: list[dict[str, str]] = []
        for s in linear:
            out.append({"name": s, "status": "done" if s != "awaiting_approval" else "rejected"})
        out.append({"name": "rejected", "status": "active"})
        return out
    out = []
    seen_active = False
    for s in linear:
        if s == phase:
            out.append({"name": s, "status": "active"})
            seen_active = True
        elif not seen_active:
            out.append({"name": s, "status": "done"})
        else:
            out.append({"name": s, "status": "upcoming"})
    if phase == "applied":
        out.append({"name": "applied", "status": "active"})
    return out


def build_pane2_view(
    *,
    proposal: dict[str, Any],
    parent_edges: dict[str, float],
    parent_sha: str,
    gate_result: dict[str, Any],
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Pane 2 context: gate states, diff, scores, rollback — evidence only."""
    gates = gate_result.get("gates") or {}
    phase = derive_pane2_phase(gates, str(gate_result.get("status") or "pending"))
    apply_report = gate_result.get("apply_report") or {}
    imp = gate_result.get("improvement") or {}
    dmg = gate_result.get("damage") or {}
    return {
        "proposal_id": proposal.get("proposal_id") or proposal.get("id") or "—",
        "action": proposal.get("action"),
        "phase": phase,
        "timeline": build_state_timeline(phase),
        "gates": gates,
        "status": gate_result.get("status"),
        "error": gate_result.get("error"),
        "diff_hunks": apply_report.get("hunks") or [],
        "scores": {
            "improvement": imp,
            "damage": dmg,
        },
        "evidence_ids": evidence_ids or list(proposal.get("evidence_ids") or []),
        "parent_sha": parent_sha,
        "sandbox_id": apply_report.get("sandbox_id"),
        "rollback_artifact": gate_result.get("rollback_artifact"),
        "canonical_hash": (gate_result.get("canonical_write") or {}).get("content_hash"),
        "approval_id": gate_result.get("approval_id"),
    }
