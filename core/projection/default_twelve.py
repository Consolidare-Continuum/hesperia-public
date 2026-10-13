# HESPERIA — Default twelve-area macro helpers (core grain).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Default area grain helpers — always 12 unless a module opts into ten-area packing."""

from __future__ import annotations

from typing import Sequence

from core.topology.invariant_catalog import AREAS, CANONICAL_AREA_ORDER


def project_default_twelve_macro(
    area_activation: Sequence[float] | None,
) -> tuple[list[float], int]:
    """
    Normalize a length-``AREAS`` (12) macro vector — default core/module path.

    Pads missing slots with 0.0; renormalizes to sum≈1.
    Returns ``(macro_vector, dominant_index)``.
    """
    src = list(area_activation or [])
    full = [float(src[i]) if i < len(src) else 0.0 for i in range(AREAS)]
    s = sum(full) or 1.0
    macro = [x / s for x in full]
    dom = max(range(len(macro)), key=lambda i: macro[i]) if macro else 0
    return macro, dom


def area_name_at(index: int) -> str:
    """Sealed area name for index in default order (GOOD…DECEIT)."""
    if not (0 <= index < len(CANONICAL_AREA_ORDER)):
        raise IndexError(f"area index out of range: {index}")
    return CANONICAL_AREA_ORDER[index]
