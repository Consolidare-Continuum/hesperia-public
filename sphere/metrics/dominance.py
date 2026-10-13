# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dominant structure detection — orchestration only; math lives in core.math.
"""

from __future__ import annotations

from core.math.vector_ops import (
    DEFAULT_NUM_AREAS,
    DEFAULT_NUM_FAMILIES,
    detect_dominant_area,
    detect_dominant_family,
    detect_family_peaks,
)

TOTAL_FAMILIES = DEFAULT_NUM_FAMILIES
TOTAL_AREAS = DEFAULT_NUM_AREAS

__all__ = [
    "detect_dominant_area",
    "detect_dominant_family",
    "detect_family_peaks",
    "TOTAL_FAMILIES",
    "TOTAL_AREAS",
]
