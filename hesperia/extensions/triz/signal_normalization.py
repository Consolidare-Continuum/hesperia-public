# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Noise reduction and threshold constants for TRIZ layer.

MOVED 2026-07-31: the smoothing/normalization functions now live in
core.math.signal_normalization (pure math, no TRIZ semantics) and are re-exported here
for backward compatibility. The threshold constants below are TRIZ-domain calibration
values and stay here.
"""

from __future__ import annotations

from core.math.signal_normalization import (
    exponential_smoothing,
    moving_average,
    z_score_normalize,
)

# Task 6.2 — threshold filters
MIN_CONTRADICTION_SCORE = 0.15
MIN_CLUSTER_SIZE = 3
MIN_PROPAGATION_STEPS = 2

__all__ = [
    "MIN_CONTRADICTION_SCORE",
    "MIN_CLUSTER_SIZE",
    "MIN_PROPAGATION_STEPS",
    "exponential_smoothing",
    "moving_average",
    "z_score_normalize",
]
