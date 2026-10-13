# HESPERIA 0.7.0 apply executor — update_edge_weight only.
from __future__ import annotations

from typing import Any

from runtime.h070_apply.sandbox import _edge_key, sandbox_diff


ALLOWED_ACTIONS = frozenset({"update_edge_weight"})


def apply_update_edge_weight(
    sandbox: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    """Apply single allowlisted proposal on sandbox copy; return diff report."""
    action = proposal.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"action not allowlisted: {action}")
    source = str(proposal.get("source") or "")
    target = str(proposal.get("target") or "")
    if not source or not target:
        raise ValueError("source and target required")
    key = _edge_key(source, target)
    before_edges = dict(sandbox["edges"])
    after_edges = dict(before_edges)
    proposed = float(proposal.get("W_e_proposed"))
    after_edges[key] = proposed
    sandbox["edges"] = after_edges
    hunks = sandbox_diff(before_edges, after_edges)
    return {
        "sandbox_id": sandbox["sandbox_id"],
        "action": action,
        "edge": key,
        "value_before": before_edges.get(key),
        "value_after": proposed,
        "hunks": hunks,
        "deterministic": len(hunks) == 1,
    }
