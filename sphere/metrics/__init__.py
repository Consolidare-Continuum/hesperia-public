# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Structural metrics: entropy, coverage, dominance, tension, loopability.
from sphere.metrics.entropy import compute_entropy, compute_normalized_entropy
from sphere.metrics.coverage import (
    compute_family_coverage,
    compute_area_coverage,
    TOTAL_FAMILIES,
    TOTAL_AREAS,
)
from sphere.metrics.dominance import (
    detect_dominant_area,
    detect_dominant_family,
    detect_family_peaks,
)
from sphere.metrics.tension import compute_structural_tension
from sphere.metrics.loopability import compute_loopability

__all__ = [
    "compute_entropy",
    "compute_normalized_entropy",
    "compute_family_coverage",
    "compute_area_coverage",
    "TOTAL_FAMILIES",
    "TOTAL_AREAS",
    "detect_dominant_area",
    "detect_dominant_family",
    "detect_family_peaks",
    "compute_structural_tension",
    "compute_loopability",
    "aggregate_structural_metrics",
]


def aggregate_structural_metrics(
    family_counts,
    area_vector,
    area_sequence,
    *,
    family_peaks_k: int = 5,
):
    """
    Build canonical metrics dict from family_counts, area_vector, area_sequence.
    Suitable for USF generator raw_metrics input.
    """
    import numpy as np
    fc = np.asarray(family_counts, dtype=np.float64)
    av = np.asarray(area_vector, dtype=np.float64)
    return {
        "entropy": compute_entropy(av),
        "normalized_entropy": compute_normalized_entropy(av),
        "coverage": compute_family_coverage(fc),
        "dominant_area": detect_dominant_area(av),
        "dominant_family": detect_dominant_family(fc),
        "family_peaks": detect_family_peaks(fc, k=family_peaks_k),
        "tension": compute_structural_tension(av),
        "loopability": compute_loopability(area_sequence),
    }
