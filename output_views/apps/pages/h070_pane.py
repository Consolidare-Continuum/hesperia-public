"""H070 Pane 2 bridge for Django Session Inspector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from django.conf import settings


def _ensure_runtime_path() -> None:
    root = Path(settings.HESPERIA_ROOT)
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)


def pane2_from_iteration(it: dict[str, Any]) -> dict[str, Any] | None:
    """Load or compute Pane 2 view from iteration `h070_apply` block."""
    block = it.get("h070_apply")
    if not isinstance(block, dict):
        return None
    _ensure_runtime_path()
    from runtime.h070_apply.gates import run_gate_chain
    from runtime.h070_apply.inspector import build_pane2_view

    proposal = block.get("proposal") or {}
    parent_edges = block.get("parent_edges") or {}
    parent_sha = str(block.get("parent_sha") or "fixture-parent")
    precomputed = block.get("gate_result")
    if isinstance(precomputed, dict):
        gate_result = precomputed
    else:
        gate_result = run_gate_chain(
            proposal=proposal,
            parent_sha=parent_sha,
            parent_edges=parent_edges,
            approval_id=block.get("approval_id"),
            baseline_incidents=int(block.get("baseline_incidents") or 0),
            after_incidents=int(block.get("after_incidents") or 0),
        )
    return build_pane2_view(
        proposal=proposal,
        parent_edges=parent_edges,
        parent_sha=parent_sha,
        gate_result=gate_result,
        evidence_ids=block.get("evidence_ids"),
    )
