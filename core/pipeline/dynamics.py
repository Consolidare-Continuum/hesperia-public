"""Pipeline stage: state evolution via operator."""

from __future__ import annotations

from core.hexmap.dynamics import (
    apply_decay,
    apply_decay_with_diagnostics,
    concentration_index,
    dispersion_index,
    smooth_toward_mean,
)

__all__ = [
    "apply_decay",
    "apply_decay_with_diagnostics",
    "concentration_index",
    "dispersion_index",
    "smooth_toward_mean",
]

