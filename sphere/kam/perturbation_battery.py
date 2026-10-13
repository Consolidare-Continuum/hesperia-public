# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Perturbation battery P1–P6 — offline stubs (P2+P3 first). No new propagation physics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from sphere.kam.bounds import KamBounds, load_kam_bounds
from sphere.kam.sisr import path_overlap
from sphere.kam.trajectory_fingerprint import SemanticTrajectoryFingerprint

# Catalog ids (contract / SPEC-v01)
P1_PARAPHRASE = "P1_paraphrase"
P2_SHADOW = "P2_shadow_context"
P3_EDGE = "P3_edge_weight_epsilon"
P4_TEACHER = "P4_teacher_proposal_preview"
P5_BRIDGE = "P5_missing_bridge_sandbox"
P6_BIAS = "P6_bias_context_inject"

ALL_PERTURBATION_IDS = (
    P1_PARAPHRASE,
    P2_SHADOW,
    P3_EDGE,
    P4_TEACHER,
    P5_BRIDGE,
    P6_BIAS,
)


@dataclass(frozen=True, slots=True)
class PerturbationRow:
    id: str
    params: dict[str, Any]
    path_survival: float
    concept_flip: float
    family_resonance: float
    area_drift: float
    contradiction_growth: float
    dominant_area_flipped: bool = False
    skipped: bool = False
    skip_reason: str | None = None
    perturbed_paths: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "params": dict(self.params),
            "path_survival": self.path_survival,
            "concept_flip": self.concept_flip,
            "family_resonance": self.family_resonance,
            "area_drift": self.area_drift,
            "contradiction_growth": self.contradiction_growth,
            "dominant_area_flipped": self.dominant_area_flipped,
        }
        if self.skipped:
            d["skipped"] = True
            d["skip_reason"] = self.skip_reason
        return d


@dataclass
class BatteryResult:
    rows: list[PerturbationRow] = field(default_factory=list)
    fragile_points: list[dict[str, Any]] = field(default_factory=list)
    incomplete: bool = False
    incomplete_reasons: list[str] = field(default_factory=list)

    @property
    def active_rows(self) -> list[PerturbationRow]:
        return [r for r in self.rows if not r.skipped]


def _drop_paths(paths: Sequence[str], drop_ratio: float) -> tuple[str, ...]:
    if not paths:
        return ()
    keep = max(0, int(round(len(paths) * (1.0 - drop_ratio))))
    return tuple(paths[:keep])


def _offline_p2(
    baseline: SemanticTrajectoryFingerprint,
    bounds: KamBounds,
) -> PerturbationRow:
    """P2 shadow-context stub — deterministic path attrition from ε_shadow."""
    eps = bounds.epsilon_shadow
    # Small ε → modest survival drop; scale so ε=0.05 ≈ drop ~1 path when |Π*|≥2.
    drop_ratio = min(0.5, eps * 5.0)
    pert_paths = _drop_paths(baseline.critical_paths, drop_ratio)
    survival = path_overlap(baseline.critical_paths, pert_paths)
    return PerturbationRow(
        id=P2_SHADOW,
        params={"epsilon_shadow": eps},
        path_survival=survival,
        concept_flip=min(1.0, eps * 1.6),
        family_resonance=max(0.0, 1.0 - eps * 2.0),
        area_drift=min(1.0, eps * 1.2),
        contradiction_growth=min(1.0, eps * 0.4),
        dominant_area_flipped=False,
        perturbed_paths=pert_paths,
    )


def _offline_p3(
    baseline: SemanticTrajectoryFingerprint,
    bounds: KamBounds,
) -> PerturbationRow:
    """P3 edge-weight ±ε stub — stronger local sensitivity than P2."""
    eps = bounds.epsilon_edge
    drop_ratio = min(0.75, eps * 25.0)  # ε=0.02 → ~0.5 drop
    pert_paths = _drop_paths(baseline.critical_paths, drop_ratio)
    survival = path_overlap(baseline.critical_paths, pert_paths)
    flipped = drop_ratio >= 0.5 and bool(baseline.dominant_area)
    return PerturbationRow(
        id=P3_EDGE,
        params={
            "epsilon_edge": eps,
            "edge": (
                f"{baseline.dominant_concept}->{baseline.concepts_activated[1][0]}"
                if len(baseline.concepts_activated) >= 2
                else "edge:unknown"
            ),
        },
        path_survival=survival,
        concept_flip=min(1.0, eps * 6.0),
        family_resonance=max(0.0, 1.0 - eps * 6.0),
        area_drift=min(1.0, eps * 5.5),
        contradiction_growth=min(1.0, eps * 4.5),
        dominant_area_flipped=flipped,
        perturbed_paths=pert_paths,
    )


def _skip_row(pid: str, reason: str, params: dict[str, Any] | None = None) -> PerturbationRow:
    return PerturbationRow(
        id=pid,
        params=params or {},
        path_survival=0.0,
        concept_flip=0.0,
        family_resonance=0.0,
        area_drift=0.0,
        contradiction_growth=0.0,
        skipped=True,
        skip_reason=reason,
    )


_RUNNERS: dict[str, Callable[[SemanticTrajectoryFingerprint, KamBounds, Mapping[str, Any]], PerturbationRow]] = {}


def _register_runners() -> None:
    def p2(b, bounds, _ctx):
        return _offline_p2(b, bounds)

    def p3(b, bounds, _ctx):
        return _offline_p3(b, bounds)

    def p1(b, bounds, _ctx):
        return _skip_row(P1_PARAPHRASE, "not_implemented_v01_offline")

    def p4(b, bounds, ctx):
        if not ctx.get("teacher_proposal"):
            return _skip_row(
                P4_TEACHER,
                "teacher_proposal_absent",
                {"requires": "Teacher inspect packet"},
            )
        # Minimal overlay stub when proposal present: treat as mild survival hit.
        eps = 0.03
        pert_paths = _drop_paths(b.critical_paths, eps * 4.0)
        return PerturbationRow(
            id=P4_TEACHER,
            params={"mode": "teacher_preview", "epsilon": eps},
            path_survival=path_overlap(b.critical_paths, pert_paths),
            concept_flip=0.05,
            family_resonance=0.92,
            area_drift=0.04,
            contradiction_growth=0.01,
            perturbed_paths=pert_paths,
        )

    def p5(b, bounds, ctx):
        if not ctx.get("sandbox_bridge_fixture"):
            return _skip_row(
                P5_BRIDGE,
                "sandbox_bridge_fixture_absent",
                {"requires": "KSI-Inspector sandbox fixture"},
            )
        eps = 0.04
        pert_paths = _drop_paths(b.critical_paths, eps * 5.0)
        return PerturbationRow(
            id=P5_BRIDGE,
            params={"mode": "missing_bridge_sandbox", "epsilon": eps},
            path_survival=path_overlap(b.critical_paths, pert_paths),
            concept_flip=0.07,
            family_resonance=0.9,
            area_drift=0.05,
            contradiction_growth=0.03,
            perturbed_paths=pert_paths,
        )

    def p6(b, bounds, _ctx):
        return _skip_row(
            P6_BIAS,
            "not_implemented_v01_offline",
            {"epsilon_bias": bounds.epsilon_bias},
        )

    _RUNNERS[P1_PARAPHRASE] = p1
    _RUNNERS[P2_SHADOW] = p2
    _RUNNERS[P3_EDGE] = p3
    _RUNNERS[P4_TEACHER] = p4
    _RUNNERS[P5_BRIDGE] = p5
    _RUNNERS[P6_BIAS] = p6


_register_runners()


def run_perturbation_battery(
    baseline: SemanticTrajectoryFingerprint,
    *,
    bounds: KamBounds | None = None,
    active: Sequence[str] | None = None,
    context: Mapping[str, Any] | None = None,
) -> BatteryResult:
    """Run offline perturbation battery. Skipped rows are excluded from 𝒫 / SISR.

    P4/P5 require Teacher / sandbox surfaces; absent → skip + battery incomplete
    (do not pretend full 𝒫).
    """
    b = bounds or load_kam_bounds()
    ctx = dict(context or {})
    want = list(active) if active is not None else list(b.active_perturbations_default)
    result = BatteryResult()

    for pid in want:
        runner = _RUNNERS.get(pid)
        if runner is None:
            row = _skip_row(pid, "unknown_perturbation_id")
        else:
            row = runner(baseline, b, ctx)
        result.rows.append(row)
        if row.skipped:
            result.incomplete = True
            result.incomplete_reasons.append(f"{pid}:{row.skip_reason}")
            result.fragile_points.append(
                {
                    "type": "perturbation_skip",
                    "id": pid,
                    "first_break_perturbation": pid,
                    "reason": row.skip_reason,
                }
            )
        elif row.path_survival < b.tau_path and baseline.critical_paths:
            # First-breaking style fragile point (stub).
            broken = [
                p
                for p in baseline.critical_paths
                if p not in set(row.perturbed_paths)
            ]
            if broken:
                result.fragile_points.append(
                    {
                        "type": "corridor",
                        "id": broken[0],
                        "first_break_perturbation": pid,
                    }
                )
    return result
