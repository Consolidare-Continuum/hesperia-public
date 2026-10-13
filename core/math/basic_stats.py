# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Basic scalar/list statistics: clamp, mean, population variance.
Deterministic; pure numerical operations only.

Graduated to core 2026-07-31 — ``clamp01`` was duplicated verbatim across 5 files in
hesperia/extensions/triz/ (crossplane_contradiction.py, contradiction_negation.py,
contradiction_uncertainty.py, contradiction_feedback.py, family_contradiction.py);
``mean``/``variance`` came from crossplane_contradiction.py. No domain semantics in any
of these — pure numeric primitives.
"""

from __future__ import annotations

import math


def clamp01(x: float) -> float:
    """Clamp to [0,1]; non-finite input (NaN/inf) returns 0.0."""
    if not math.isfinite(x):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def mean(xs: list[float]) -> float:
    """Arithmetic mean; empty list returns 0.0."""
    if not xs:
        return 0.0
    return float(sum(xs)) / float(len(xs))


def variance(xs: list[float]) -> float:
    """Population variance; fewer than 2 values returns 0.0."""
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return float(sum((x - m) ** 2 for x in xs)) / float(len(xs))


__all__ = [
    "clamp01",
    "mean",
    "variance",
]
