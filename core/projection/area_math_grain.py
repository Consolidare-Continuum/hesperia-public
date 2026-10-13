# HESPERIA — Area-math grain classifier (10-total vs 12-total).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Classifier switch for area-total math grains.

Two lawful grains:

| Grain | Total areas | Families (pack) | Role |
|-------|-------------|-----------------|------|
| ``12`` | 12 | 288 | **Default** core + default module math |
| ``10`` | 10 | 240 | Optional module packing (drops sealed 10–11) |

Env (canonical):

- ``HESPERIA_AREA_MATH_GRAIN=12`` (default) or ``10``
- Legacy alias: ``HESPERIA_TEN_AREA_MODULE=1`` → grain ``10``

Geometry lock ``AREAS=12`` in ``invariant_catalog`` stays; grain ``10`` is a
classifier-selected packing over that lock, not a second geometry constant.
"""

from __future__ import annotations

import os
from typing import Any, Literal, Sequence

from core.projection.default_twelve import project_default_twelve_macro
from core.projection.ten_area_module import (
    TEN_AREA_COUNT,
    TEN_AREA_FAMILY_COUNT,
    project_ten_area_macro,
)
from core.topology.invariant_catalog import AREAS, FAMILIES_PER_AREA, TOTAL_FAMILIES

AreaMathGrain = Literal[10, 12]

_TRUTHY = ("1", "true", "yes", "on")
_ENV_GRAIN = "HESPERIA_AREA_MATH_GRAIN"
_ENV_TEN_ALIAS = "HESPERIA_TEN_AREA_MODULE"


def _parse_grain(raw: str | None) -> AreaMathGrain | None:
    if raw is None:
        return None
    s = raw.strip().lower()
    if not s:
        return None
    if s in ("12", "twelve", "default", "full"):
        return 12
    if s in ("10", "ten"):
        return 10
    raise ValueError(
        f"invalid {_ENV_GRAIN}={raw!r}; expected 12|10 (or twelve|ten|default|full)"
    )


def classify_area_math_grain(
    *,
    explicit: AreaMathGrain | int | str | None = None,
) -> AreaMathGrain:
    """
    Resolve active area-math grain.

    Precedence: ``explicit`` arg → ``HESPERIA_AREA_MATH_GRAIN`` →
    ``HESPERIA_TEN_AREA_MODULE`` truthy → default ``12``.
    """
    if explicit is not None:
        if isinstance(explicit, int):
            if explicit in (10, 12):
                return explicit  # type: ignore[return-value]
            raise ValueError(f"explicit grain must be 10 or 12, got {explicit}")
        parsed = _parse_grain(str(explicit))
        if parsed is None:
            raise ValueError(f"explicit grain empty: {explicit!r}")
        return parsed

    env_grain = _parse_grain(os.environ.get(_ENV_GRAIN))
    if env_grain is not None:
        return env_grain

    if os.environ.get(_ENV_TEN_ALIAS, "0").strip().lower() in _TRUTHY:
        return 10

    return 12


def area_math_grain() -> AreaMathGrain:
    """Active grain from env/defaults (no explicit override)."""
    return classify_area_math_grain()


def area_math_totals(grain: AreaMathGrain | None = None) -> dict[str, int]:
    """Totals for the selected grain (pack sizes for macro / family public cuts)."""
    g = grain if grain is not None else area_math_grain()
    if g == 10:
        return {
            "grain": 10,
            "areas": TEN_AREA_COUNT,
            "families": TEN_AREA_FAMILY_COUNT,
            "families_per_area": FAMILIES_PER_AREA,
            "geometry_areas_lock": AREAS,
            "geometry_families_lock": TOTAL_FAMILIES,
        }
    return {
        "grain": 12,
        "areas": AREAS,
        "families": TOTAL_FAMILIES,
        "families_per_area": FAMILIES_PER_AREA,
        "geometry_areas_lock": AREAS,
        "geometry_families_lock": TOTAL_FAMILIES,
    }


def project_macro_for_grain(
    area_activation: Sequence[float] | None,
    *,
    grain: AreaMathGrain | None = None,
) -> tuple[list[float], int, AreaMathGrain]:
    """
    Project/normalize macro vector under the classified grain.

    Returns ``(macro_vector, dominant_index, grain_used)``.
    """
    g = grain if grain is not None else classify_area_math_grain()
    if g == 10:
        macro, dom = project_ten_area_macro(area_activation)
    else:
        macro, dom = project_default_twelve_macro(area_activation)
    return macro, dom, g


def area_math_classifier_meta(
    *,
    grain: AreaMathGrain | None = None,
) -> dict[str, Any]:
    """Attachable meta block for analyze/USF — which math switch is live."""
    g = grain if grain is not None else area_math_grain()
    totals = area_math_totals(g)
    return {
        "area_math_grain": g,
        "classifier": "core.projection.area_math_grain",
        "switch_env": _ENV_GRAIN,
        "legacy_alias_env": _ENV_TEN_ALIAS,
        "totals": totals,
        "note": (
            "grain=12 is default core/module math; grain=10 is optional ten-total packing"
            if g == 12
            else "grain=10 ten-total packing; geometry lock remains AREAS=12"
        ),
    }


def ten_area_module_enabled() -> bool:
    """True when classifier resolves to grain 10 (incl. legacy alias)."""
    return area_math_grain() == 10


def active_area_count(grain: AreaMathGrain | None = None) -> int:
    return int(area_math_totals(grain)["areas"])


def active_family_count(grain: AreaMathGrain | None = None) -> int:
    return int(area_math_totals(grain)["families"])


def pack_excludes_area(area_index: int, *, grain: AreaMathGrain | None = None) -> bool:
    """True when ten-area packing drops this sealed index (10/11). Grain 12 → never."""
    g = grain if grain is not None else classify_area_math_grain()
    if g == 12:
        return False
    return area_index in (10, 11)


def pack_excludes_family(family_global_index: int, *, grain: AreaMathGrain | None = None) -> bool:
    """True when ten-area packing drops families 240–287. Grain 12 → never."""
    g = grain if grain is not None else classify_area_math_grain()
    if g == 12:
        return False
    return 240 <= int(family_global_index) < 288


def slice_area_vector(
    area_activation: Sequence[float] | None,
    *,
    grain: AreaMathGrain | None = None,
) -> list[float]:
    """Slice/pad area activation to active grain length (no renormalize)."""
    g = grain if grain is not None else classify_area_math_grain()
    n = active_area_count(g)
    src = list(area_activation or [])
    return [float(src[i]) if i < len(src) else 0.0 for i in range(n)]


def slice_family_vector(
    family_counts: Sequence[float] | Sequence[int] | None,
    *,
    grain: AreaMathGrain | None = None,
) -> list[float]:
    """Slice family vector to active grain family count (no renormalize)."""
    g = grain if grain is not None else classify_area_math_grain()
    n = active_family_count(g)
    src = list(family_counts or [])
    return [float(src[i]) if i < len(src) else 0.0 for i in range(n)]
