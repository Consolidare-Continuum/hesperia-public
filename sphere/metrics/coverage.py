# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural coverage — orchestration only; math lives in core.math.
"""

from __future__ import annotations

from core.math.coverage import (
    DEFAULT_NUM_AREAS,
    DEFAULT_NUM_FAMILIES,
    compute_area_coverage,
    compute_family_coverage,
)

TOTAL_FAMILIES = DEFAULT_NUM_FAMILIES
TOTAL_AREAS = DEFAULT_NUM_AREAS

__all__ = [
    "compute_family_coverage",
    "compute_area_coverage",
    "TOTAL_FAMILIES",
    "TOTAL_AREAS",
]
