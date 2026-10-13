# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""KAM_semantic_score composite + kam_verdict bands (inspection lens; not a theorem)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from sphere.kam.bounds import KamBounds, load_kam_bounds
from sphere.kam.sisr import SisrResult

KamVerdict = Literal[
    "structurally_robust",
    "conditionally_stable",
    "fragile_trajectory",
    "insufficient_baseline",
]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True, slots=True)
class KamScoreComponents:
    path_survival: float
    area_stability: float
    contradiction_non_growth: float
    resonance_penalty_inverse: float
    drift_penalty_inverse: float

    def as_dict(self) -> dict[str, float]:
        return {
            "path_survival": self.path_survival,
            "area_stability": self.area_stability,
            "contradiction_non_growth": self.contradiction_non_growth,
            "resonance_penalty_inverse": self.resonance_penalty_inverse,
            "drift_penalty_inverse": self.drift_penalty_inverse,
        }


@dataclass(frozen=True, slots=True)
class KamScoreResult:
    KAM_semantic_score: float | None
    kam_verdict: KamVerdict
    components: KamScoreComponents | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "KAM_semantic_score": self.KAM_semantic_score,
            "kam_verdict": self.kam_verdict,
            "components": None if self.components is None else self.components.as_dict(),
        }


def verdict_from_score(
    score: float | None,
    *,
    bounds: KamBounds | None = None,
) -> KamVerdict:
    """Map score → kam_verdict bands (contract §43).

    Boundaries: ≥ 0.75 structurally_robust; 0.45 ≤ score < 0.75 conditionally_stable;
    < 0.45 fragile_trajectory; null → insufficient_baseline.
    Mid-band lower bound is inclusive.
    """
    if score is None:
        return "insufficient_baseline"
    b = bounds or load_kam_bounds()
    s = float(score)
    if s >= b.structurally_robust_min:
        return "structurally_robust"
    if s >= b.conditionally_stable_min:
        return "conditionally_stable"
    return "fragile_trajectory"


def compute_kam_semantic_score(
    sisr: SisrResult,
    *,
    area_drift_mean: float,
    contradiction_growth_mean: float,
    family_resonance_mean: float,
    dominant_area_flip_rate: float,
    bounds: KamBounds | None = None,
) -> KamScoreResult:
    """Multiplicative composite — any near-zero factor collapses the score."""
    b = bounds or load_kam_bounds()
    if sisr.empty_baseline or sisr.SISR_min is None or sisr.SISR_mean is None:
        return KamScoreResult(
            KAM_semantic_score=None,
            kam_verdict="insufficient_baseline",
            components=None,
        )

    if b.path_survival_uses == "SISR_mean":
        path_survival = float(sisr.SISR_mean)
    else:
        path_survival = float(sisr.SISR_min)

    components = KamScoreComponents(
        path_survival=clamp01(path_survival),
        area_stability=clamp01(1.0 - clamp01(area_drift_mean)),
        contradiction_non_growth=clamp01(1.0 - clamp01(contradiction_growth_mean)),
        resonance_penalty_inverse=clamp01(family_resonance_mean),
        drift_penalty_inverse=clamp01(1.0 - clamp01(dominant_area_flip_rate)),
    )
    score = (
        components.path_survival
        * components.area_stability
        * components.contradiction_non_growth
        * components.resonance_penalty_inverse
        * components.drift_penalty_inverse
    )
    score = clamp01(score)
    return KamScoreResult(
        KAM_semantic_score=score,
        kam_verdict=verdict_from_score(score, bounds=b),
        components=components,
    )


def aggregate_measures(
    perturbation_rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """Mean area_drift / contradiction_growth / family_resonance + flip rate."""
    if not perturbation_rows:
        return {
            "area_drift_mean": 0.0,
            "contradiction_growth_mean": 0.0,
            "family_resonance_mean": 0.0,
            "dominant_area_flip_rate": 0.0,
        }
    n = float(len(perturbation_rows))
    area = sum(float(r.get("area_drift", 0.0) or 0.0) for r in perturbation_rows) / n
    cg = (
        sum(float(r.get("contradiction_growth", 0.0) or 0.0) for r in perturbation_rows)
        / n
    )
    fr = (
        sum(float(r.get("family_resonance", 0.0) or 0.0) for r in perturbation_rows) / n
    )
    flips = sum(1 for r in perturbation_rows if r.get("dominant_area_flipped"))
    return {
        "area_drift_mean": area,
        "contradiction_growth_mean": cg,
        "family_resonance_mean": fr,
        "dominant_area_flip_rate": flips / n,
    }
