# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Matrix utilities: row-normalize, shape checks.
Deterministic; pure numerical operations only.
"""

from __future__ import annotations

import numpy as np


def row_normalize(matrix: np.ndarray, *, fill_zero_rows: float = 0.0) -> np.ndarray:
    """
    Row-normalize so each row sums to 1. Zero-sum rows get fill_zero_rows (default 0).
    Returns float64 array.
    """
    arr = np.asarray(matrix, dtype=np.float64)
    row_sums = arr.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(row_sums > 0, arr / row_sums, fill_zero_rows)
    return np.asarray(out, dtype=np.float64)
