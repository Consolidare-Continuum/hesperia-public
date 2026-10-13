# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Wraps Sigma/Gamma/Theta guard results as fpf Guard functions."""

from __future__ import annotations

from typing import Any

from fpf_thinking_map.guards import Guard, GuardResult, GuardScope, GuardVerdict
from fpf_thinking_map.state import ActiveState


def _make_sigma_guard(sigma: dict[str, Any]) -> Guard:
    """Sigma (static invariant) guard — pre-evaluated closure."""
    passed = bool(sigma.get("passed", True))
    failed_checks = sigma.get("failed_checks") or []
    first_failure = ""
    if failed_checks:
        first = failed_checks[0]
        first_failure = str(first.get("message", first.get("invariant_id", "sigma_violation")))

    def _check(state: ActiveState, _transition_id: str | None) -> GuardResult:
        if passed:
            return GuardResult("hesperia_sigma", GuardVerdict.ALLOW)
        return GuardResult("hesperia_sigma", GuardVerdict.DENY, f"Sigma invariant failed: {first_failure}")

    return Guard("hesperia_sigma", GuardScope.GLOBAL, _check)


def _make_gamma_guard(gamma: dict[str, Any]) -> Guard:
    """Gamma (dynamic invariant) guard — pre-evaluated closure."""
    passed = bool(gamma.get("passed", True))
    failed_checks = gamma.get("failed_checks") or []
    reasons = [str(c.get("message", c.get("invariant_id", ""))) for c in failed_checks if isinstance(c, dict)]

    def _check(state: ActiveState, _transition_id: str | None) -> GuardResult:
        if passed:
            return GuardResult("hesperia_gamma", GuardVerdict.ALLOW)
        return GuardResult("hesperia_gamma", GuardVerdict.DENY, f"Gamma invariant failed: {'; '.join(reasons)}")

    return Guard("hesperia_gamma", GuardScope.GLOBAL, _check)


def _make_theta_guard(theta: dict[str, Any]) -> Guard:
    """Theta (governance) guard — pre-evaluated closure."""
    approved = bool(theta.get("approved", True))
    warnings = theta.get("warnings") or []
    violations = theta.get("violations") or []

    def _check(state: ActiveState, _transition_id: str | None) -> GuardResult:
        if not approved:
            detail = "; ".join(str(v) for v in violations) if violations else "governance_denied"
            return GuardResult("hesperia_theta", GuardVerdict.DENY, f"Theta governance denied: {detail}")
        if warnings:
            detail = "; ".join(str(w) for w in warnings)
            return GuardResult("hesperia_theta", GuardVerdict.WARN, f"Theta governance warnings: {detail}")
        return GuardResult("hesperia_theta", GuardVerdict.ALLOW)

    return Guard("hesperia_theta", GuardScope.GLOBAL, _check)


def build_hesperia_guards(guards_result: dict[str, Any]) -> list[Guard]:
    """Build fpf Guard list from sphere Sigma/Gamma/Theta results."""
    sigma = guards_result.get("sigma") or {}
    gamma = guards_result.get("gamma") or {}
    theta = guards_result.get("theta") or {}
    return [
        _make_sigma_guard(sigma),
        _make_gamma_guard(gamma),
        _make_theta_guard(theta),
    ]
