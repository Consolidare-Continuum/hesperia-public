# HESPERIA — Optional ten-area module packing (NOT default core).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Ten-area module grain — optional packing over the 12-area core.

**Default core and default module = 12 areas** (GOOD…DECEIT), ``AREAS`` in
``core.topology.invariant_catalog``.

This module holds **10-total math helpers** (indices 0–9, 240 families).
Classifier switch (which grain is active): ``core.projection.area_math_grain``
via ``HESPERIA_AREA_MATH_GRAIN=10|12`` (legacy ``HESPERIA_TEN_AREA_MODULE=1`` → 10).
"""

from __future__ import annotations

import os
from typing import Sequence

_TRUTHY = ("1", "true", "yes", "on")

# Ten-area module constants (optional packing — not core geometry).
TEN_AREA_COUNT = 10
TEN_AREA_FAMILY_COUNT = 240
# Sealed indices treated as out-of-pack for this module only (see assets/reserve/).
TEN_AREA_EXCLUDED_INDICES = frozenset({10, 11})


def ten_area_alias_env_enabled() -> bool:
    """Legacy env only — prefer ``area_math_grain.classify_area_math_grain()``."""
    return os.environ.get("HESPERIA_TEN_AREA_MODULE", "0").strip().lower() in _TRUTHY


def ten_area_module_enabled() -> bool:
    """True when active grain is 10 (classifier / env). Prefer ``area_math_grain``."""
    # Lazy import — area_math_grain imports this module.
    from core.projection.area_math_grain import classify_area_math_grain

    return classify_area_math_grain() == 10


def project_ten_area_macro(
    area_activation: Sequence[float] | None,
) -> tuple[list[float], int]:
    """
    Normalize a length-10 macro vector from a full area activation vector.

    Drops indices in ``TEN_AREA_EXCLUDED_INDICES``. Renormalizes to sum≈1.
    Returns ``(macro_vector, dominant_index)``.
    """
    src = list(area_activation or [])
    public = [
        float(src[i]) if i < len(src) else 0.0
        for i in range(TEN_AREA_COUNT)
        if i not in TEN_AREA_EXCLUDED_INDICES
    ]
    s = sum(public) or 1.0
    macro = [x / s for x in public]
    dom = max(range(len(macro)), key=lambda i: macro[i]) if macro else 0
    return macro, dom
