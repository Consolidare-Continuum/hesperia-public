# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Structural sequence metrics (e.g. loopability).
Deterministic counts and ratios. No pipeline logic.
"""

from __future__ import annotations

import numpy as np


def compute_loopability(
    area_sequence: np.ndarray | list[int],
    *,
    num_areas: int = 12,
) -> float:
    """
    Loopability = loop_events / total_transitions.

    Loop event: at position i, area_sequence[i] was seen at some j < i-1
    (i.e. we return to an area after at least one step away).
    total_transitions = len(area_sequence) - 1.

    If sequence length < 2, returns 0.0. Range [0, 1].
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    n = len(arr)
    if n < 2:
        return 0.0
    if np.any(arr < 0) or np.any(arr >= num_areas):
        raise ValueError(f"All area_sequence values must be in [0, {num_areas - 1}]")
    total_transitions = n - 1
    loop_events = 0
    for i in range(1, n):
        current = int(arr[i])
        # Check if current was seen at some j <= i-2 (distance > 1)
        for j in range(0, i - 1):
            if arr[j] == current:
                loop_events += 1
                break
    return float(loop_events / total_transitions)
