# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Conservation checks for energy/mass flows.
Deterministic; pure numerical checks only.
"""

from __future__ import annotations

import numpy as np


def check_mass_conservation(
    before: np.ndarray | list[float],
    after: np.ndarray | list[float],
    *,
    relative_tolerance: float = 1e-6,
) -> bool:
    """
    True if sum(after) is within relative_tolerance of sum(before).
    """
    s_before = float(np.sum(before))
    s_after = float(np.sum(after))
    if s_before <= 0:
        return s_after <= 0 or abs(s_after - s_before) <= relative_tolerance
    ratio = s_after / s_before
    return (1.0 - relative_tolerance) <= ratio <= (1.0 + relative_tolerance)
