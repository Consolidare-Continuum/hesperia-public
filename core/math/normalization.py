# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Normalization utilities for vectors and distributions.
Deterministic; pure numerical operations only.
"""

from __future__ import annotations

import numpy as np


def normalize_l1(vector: np.ndarray | list[float], *, eps: float = 0.0) -> np.ndarray:
    """
    L1-normalize so sum(output) == 1. Zero sum yields zeros; eps not used for divisor.
    Returns float64 array.
    """
    arr = np.asarray(vector, dtype=np.float64)
    total = float(np.sum(arr))
    if total <= 0:
        return np.zeros_like(arr, dtype=np.float64)
    return np.asarray(arr / total, dtype=np.float64)
