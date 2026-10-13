# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""KAM (research) wire entry — flag-gated inspect lens after KSI-Inspector + Teacher.

Does not alter sealed physics. When ``HESPERIA_KAM_ENABLED`` is unset/0, callers
must treat attach helpers as no-ops. Never claims KAM theorem.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence

from sphere.kam.apply_gate import inspect_apply_gate
from sphere.kam.bounds import clear_bounds_cache, load_kam_bounds
from sphere.kam.critical_paths import extract_critical_paths, with_critical_paths
from sphere.kam.flags import kam_enabled
from sphere.kam.kam_score import aggregate_measures, compute_kam_semantic_score
from sphere.kam.perturbation_battery import run_perturbation_battery
from sphere.kam.report import build_kam_report
from sphere.kam.sisr import compute_sisr
from sphere.kam.trajectory_fingerprint import build_trajectory_fingerprint


def run_kam_inspect(
    analyze_bundle: Mapping[str, Any] | None,
    *,
    active_perturbations: Sequence[str] | None = None,
    context: Mapping[str, Any] | None = None,
    nash_repair_stability_ok: bool = False,
) -> dict[str, Any]:
    """Run offline battery → SISR → KAM_semantic_score → report + apply lens.

    Returns empty disabled stub when master flag is off.
    """
    if not kam_enabled():
        return {
            "enabled": False,
            "schema": "hesperia.kam_perturbation_report.v01",
            "kam_verdict": None,
            "note": "HESPERIA_KAM_ENABLED=0 — KAM research lens inactive",
        }

    bounds = load_kam_bounds()
    fp0 = build_trajectory_fingerprint(analyze_bundle)
    paths = extract_critical_paths(fp0, analyze_bundle, bounds=bounds)
    baseline = with_critical_paths(fp0, paths)

    battery = run_perturbation_battery(
        baseline,
        bounds=bounds,
        active=active_perturbations,
        context=context,
    )
    active = battery.active_rows
    sisr = compute_sisr(
        (r.path_survival for r in active),
        baseline_path_count=len(baseline.critical_paths),
    )
    measures = aggregate_measures([r.as_dict() for r in active])
    score = compute_kam_semantic_score(sisr, bounds=bounds, **measures)
    report = build_kam_report(
        baseline,
        battery,
        sisr,
        score,
        bounds_version=bounds.version,
    )
    lens = inspect_apply_gate(
        report,
        nash_repair_stability_ok=nash_repair_stability_ok,
    )
    return {
        "enabled": True,
        "research_lens": True,
        "not_a_theorem": True,
        "stack_order_note": (
            "KAM runs after KSI-Inspector + Teacher inspect-only; "
            "neighbour lens, not L1–L9 replacement"
        ),
        "report": report,
        "apply_gate_lens": lens.as_dict(),
        "bounds": bounds.as_dict(),
    }


def attach_kam_to_engine_result(
    engine_result: MutableMapping[str, Any] | None,
    *,
    context: Mapping[str, Any] | None = None,
) -> MutableMapping[str, Any] | None:
    """Attach ``kam_stability`` read-only block when enabled; never mutates graph."""
    if engine_result is None:
        return None
    if not kam_enabled():
        return engine_result
    block = run_kam_inspect(engine_result, context=context)
    # Surface report also as engine_result.kam_stability (contract future wire).
    engine_result["kam_stability"] = block.get("report") or block
    engine_result["kam_apply_gate_lens"] = block.get("apply_gate_lens")
    return engine_result


# Re-export for tests that clear cache between cases
__all__ = [
    "attach_kam_to_engine_result",
    "clear_bounds_cache",
    "run_kam_inspect",
]
