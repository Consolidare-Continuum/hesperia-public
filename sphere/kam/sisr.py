# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""SISR — Semantic Invariant Survival Rate (research inspection scalar; not a theorem)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


def path_overlap(
    baseline_paths: Sequence[str],
    perturbed_paths: Sequence[str],
) -> float:
    """Jaccard-style overlap |Π_p ∩ Π*| / |Π*| ∈ [0, 1].

    Uses baseline cardinality in the denominator (contract §41.3). Empty Π* → 0.0
    for this helper; callers must emit null SISR via :func:`compute_sisr`.
    """
    pi_star = [str(p) for p in baseline_paths]
    if not pi_star:
        return 0.0
    pi_p = set(str(p) for p in perturbed_paths)
    inter = sum(1 for p in pi_star if p in pi_p)
    return inter / float(len(pi_star))


@dataclass(frozen=True, slots=True)
class SisrResult:
    """Aggregated SISR across active perturbation set 𝒫."""

    SISR_min: float | None
    SISR_mean: float | None
    path_survival: tuple[float, ...]
    empty_baseline: bool

    def as_dict(self) -> dict[str, float | None | list[float] | bool]:
        return {
            "SISR_min": self.SISR_min,
            "SISR_mean": self.SISR_mean,
            "path_survival": list(self.path_survival),
            "empty_baseline": self.empty_baseline,
        }


def compute_sisr(
    path_survival_values: Iterable[float],
    *,
    baseline_path_count: int,
) -> SisrResult:
    """Compute SISR_min / SISR_mean from per-p path_survival values.

    When ``|Π*| = 0``: both null (do **not** invent 1.0).
    Failed/skipped perturbations must be excluded by the caller before calling.
    """
    if baseline_path_count <= 0:
        return SisrResult(
            SISR_min=None,
            SISR_mean=None,
            path_survival=(),
            empty_baseline=True,
        )
    vals = tuple(max(0.0, min(1.0, float(v))) for v in path_survival_values)
    if not vals:
        return SisrResult(
            SISR_min=None,
            SISR_mean=None,
            path_survival=(),
            empty_baseline=False,
        )
    return SisrResult(
        SISR_min=min(vals),
        SISR_mean=sum(vals) / float(len(vals)),
        path_survival=vals,
        empty_baseline=False,
    )
