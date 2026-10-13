# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Emit ``hesperia.kam_perturbation_report.v01`` — research inspection report."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sphere.kam.kam_score import KamScoreResult
from sphere.kam.perturbation_battery import BatteryResult, PerturbationRow
from sphere.kam.sisr import SisrResult
from sphere.kam.trajectory_fingerprint import SemanticTrajectoryFingerprint

SCHEMA_ID = "hesperia.kam_perturbation_report.v01"


def _stable_islands(
    baseline: SemanticTrajectoryFingerprint,
    active_rows: Sequence[PerturbationRow],
) -> list[dict[str, Any]]:
    islands: list[dict[str, Any]] = []
    if baseline.dominant_family and active_rows:
        if all(r.family_resonance >= 0.85 for r in active_rows):
            islands.append(
                {
                    "type": "family",
                    "id": baseline.dominant_family,
                    "survived_all": True,
                }
            )
    if baseline.dominant_area and active_rows:
        if all(not r.dominant_area_flipped for r in active_rows):
            islands.append(
                {
                    "type": "path_segment",
                    "id": f"within_area:{baseline.dominant_area}",
                    "survived_all": True,
                }
            )
    if baseline.critical_paths and active_rows:
        survived = set(baseline.critical_paths)
        for r in active_rows:
            survived &= set(r.perturbed_paths)
        for pid in sorted(survived):
            islands.append({"type": "path_segment", "id": pid, "survived_all": True})
    return islands


def build_kam_report(
    baseline: SemanticTrajectoryFingerprint,
    battery: BatteryResult,
    sisr: SisrResult,
    score: KamScoreResult,
    *,
    bounds_version: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble schema-valid report dict (inspect-only; no graph mutation)."""
    active = battery.active_rows
    report: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "baseline_id": baseline.baseline_id,
        "baseline": baseline.summary(),
        "perturbations": [r.as_dict() for r in active],
        "SISR_min": sisr.SISR_min,
        "SISR_mean": sisr.SISR_mean,
        "KAM_semantic_score": score.KAM_semantic_score,
        "kam_verdict": score.kam_verdict,
        "stable_islands": _stable_islands(baseline, active),
        "fragile_points": list(battery.fragile_points),
        "meta": {
            "research_lens": True,
            "not_a_theorem": True,
            "bounds_version": bounds_version,
            "battery_incomplete": battery.incomplete,
            "incomplete_reasons": list(battery.incomplete_reasons),
            "skipped_perturbations": [
                {"id": r.id, "reason": r.skip_reason} for r in battery.rows if r.skipped
            ],
            "components": None if score.components is None else score.components.as_dict(),
        },
    }
    if extra:
        report["meta"].update(dict(extra))
    return report
