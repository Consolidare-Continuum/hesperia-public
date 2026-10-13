# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""KAM apply-gate lens — inspect-only pre-0.7.0; does not mutate graph or widen allowlist.

Hard rule: this module is a neighbour stability lens after KSI-Inspector + Teacher.
It does **not** claim the KAM theorem and does **not** call apply executors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from sphere.kam.flags import kam_inspect_only
from sphere.kam.kam_score import KamVerdict

ApplyLensStatus = Literal[
    "inspect_only",
    "allow_candidate",
    "review_required",
    "hard_block",
]


@dataclass(frozen=True, slots=True)
class KamApplyGateLens:
    """Inspect-only gate evaluation from a prior KAM report."""

    status: ApplyLensStatus
    kam_verdict: KamVerdict | str | None
    allow_sandbox_apply_candidate: bool
    mutates_graph: bool
    reasons: tuple[str, ...]
    baseline_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "kam_verdict": self.kam_verdict,
            "allow_sandbox_apply_candidate": self.allow_sandbox_apply_candidate,
            "mutates_graph": self.mutates_graph,
            "reasons": list(self.reasons),
            "baseline_id": self.baseline_id,
            "mode": "inspect",
            "note": (
                "KAM (research) apply-gate lens — inspect-only pre-0.7.0; "
                "not a theorem; does not widen 0.7.0 allowlist"
            ),
        }


def inspect_apply_gate(
    kam_report: Mapping[str, Any] | None,
    *,
    nash_repair_stability_ok: bool = False,
    force_apply_mode: bool = False,
) -> KamApplyGateLens:
    """Evaluate apply candidacy from an existing KAM report (read-only).

    Pre-0.7.0 (``HESPERIA_KAM_INSPECT_ONLY`` default on): always returns
    ``inspect_only`` / ``mutates_graph=False`` even when verdict is robust —
    apply consumption is deferred until 0.7.0 sandbox gates consume the report.

    When inspect-only is off (future 0.7.0 wire), still **never** mutates here;
    only emits ``allow_sandbox_apply_candidate`` for G1–G9 + allowlist consumers.
    """
    report = dict(kam_report or {})
    verdict = report.get("kam_verdict")
    baseline_id = report.get("baseline_id")
    reasons: list[str] = []

    if not report:
        reasons.append("missing_kam_report")
        return KamApplyGateLens(
            status="hard_block",
            kam_verdict=None,
            allow_sandbox_apply_candidate=False,
            mutates_graph=False,
            reasons=tuple(reasons),
            baseline_id=None,
        )

    if verdict in (None, "insufficient_baseline"):
        reasons.append("insufficient_baseline")
        status: ApplyLensStatus = "hard_block"
        allow = False
    elif verdict == "fragile_trajectory":
        reasons.append("fragile_trajectory")
        status = "hard_block"
        allow = False
    elif verdict == "conditionally_stable":
        reasons.append("conditionally_stable_requires_operator_review")
        status = "review_required"
        allow = False
    elif verdict == "structurally_robust":
        if not nash_repair_stability_ok:
            reasons.append("nash_repair_stability_not_ok")
            status = "review_required"
            allow = False
        else:
            reasons.append("structurally_robust")
            status = "allow_candidate"
            allow = True
    else:
        reasons.append(f"unknown_verdict:{verdict}")
        status = "hard_block"
        allow = False

    # Pre-0.7.0 hard rule: inspect-only — never claim apply execution here.
    if kam_inspect_only() and not force_apply_mode:
        reasons.append("pre_0.7.0_inspect_only")
        return KamApplyGateLens(
            status="inspect_only",
            kam_verdict=verdict,
            allow_sandbox_apply_candidate=False,
            mutates_graph=False,
            reasons=tuple(reasons),
            baseline_id=str(baseline_id) if baseline_id else None,
        )

    return KamApplyGateLens(
        status=status if allow or status != "allow_candidate" else status,
        kam_verdict=verdict,
        allow_sandbox_apply_candidate=allow,
        mutates_graph=False,
        reasons=tuple(reasons),
        baseline_id=str(baseline_id) if baseline_id else None,
    )
