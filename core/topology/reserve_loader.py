# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Reserve loader — optional **ten-area module** packing helpers.

Loads reserved_areas.json / reserved_families / reserved_hex for callers that opt into
ten-area packing (indices 10–11 excluded from that pack).

**Default core grain remains 12** (CREATION, DECEIT are first-class). Reserve exclusion
applies only when the area-math classifier is grain **10**
(``HESPERIA_AREA_MATH_GRAIN=10`` / legacy ``HESPERIA_TEN_AREA_MODULE=1``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Set

# Default: repo_root/assets/reserve (core/topology is core/topology, so parents[2] = repo)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RESERVE_DIR = _REPO_ROOT / "assets" / "reserve"


def _load_json(dir_path: Path, filename: str) -> dict:
    path = dir_path / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_reserved_area_indices(reserve_dir: Path | None = None) -> frozenset[int]:
    """Return set of internal area indices that are permanently reserved (service areas 10, 11)."""
    dir_path = reserve_dir or _DEFAULT_RESERVE_DIR
    data = _load_json(dir_path, "reserved_areas.json")
    indices = data.get("reserved_indices")
    if indices is not None:
        return frozenset(int(i) for i in indices)
    # Fallback: permanent lock on indices 10, 11 when file missing
    return frozenset({10, 11})


def load_reserved_family_global_indices(reserve_dir: Path | None = None) -> frozenset[int]:
    """Return set of global family indices (0..287) that are under reserved areas."""
    dir_path = reserve_dir or _DEFAULT_RESERVE_DIR
    data = _load_json(dir_path, "reserved_families_registry.json")
    indices = data.get("reserved_family_global_indices")
    if indices is not None:
        return frozenset(int(i) for i in indices)
    # Fallback: families 240..287 (areas 10 and 11, 24 families each)
    return frozenset(range(240, 288))


def load_reserved_side_id_range(reserve_dir: Path | None = None) -> tuple[int, int] | None:
    """Return (start_inclusive, end_inclusive) for reserved side_id range, or None if not configured."""
    dir_path = reserve_dir or _DEFAULT_RESERVE_DIR
    data = _load_json(dir_path, "reserved_hex_registry.json")
    r = data.get("reserved_side_id_range")
    if r:
        return (int(r["start_inclusive"]), int(r["end_inclusive"]))
    # Fallback: 48 families * 250 hexes * 6 sides = 360_000..431_999
    return (360_000, 431_999)


# Module-level cached sets (lazy load once)
_reserved_areas: Set[int] | None = None
_reserved_families: Set[int] | None = None
_reserved_side_range: tuple[int, int] | None = None


def _ensure_loaded() -> None:
    global _reserved_areas, _reserved_families, _reserved_side_range
    if _reserved_areas is None:
        _reserved_areas = set(load_reserved_area_indices())
    if _reserved_families is None:
        _reserved_families = set(load_reserved_family_global_indices())
    if _reserved_side_range is None:
        _reserved_side_range = load_reserved_side_id_range()


def is_reserved_area(area_index: int, *, grain: int | None = None) -> bool:
    """
    Ten-area pack exclusion for indices 10–11.

    Under default grain 12, returns False (CREATION/DECEIT are first-class).
    Pass ``grain=10`` to force pack exclusion regardless of env.
    """
    if grain is None:
        from core.projection.area_math_grain import classify_area_math_grain

        grain = classify_area_math_grain()
    if grain == 12:
        return False
    _ensure_loaded()
    return area_index in _reserved_areas if _reserved_areas else False


def is_reserved_family(family_global_index: int, *, grain: int | None = None) -> bool:
    """Ten-area pack exclusion for families 240–287; grain 12 → never reserved."""
    if grain is None:
        from core.projection.area_math_grain import classify_area_math_grain

        grain = classify_area_math_grain()
    if grain == 12:
        return False
    _ensure_loaded()
    return family_global_index in _reserved_families if _reserved_families else False


def is_reserved_side_id(side_id: int, *, grain: int | None = None) -> bool:
    """Ten-area pack exclusion for reserved side range; grain 12 → never reserved."""
    if grain is None:
        from core.projection.area_math_grain import classify_area_math_grain

        grain = classify_area_math_grain()
    if grain == 12:
        return False
    _ensure_loaded()
    if _reserved_side_range is None:
        return False
    lo, hi = _reserved_side_range
    return lo <= side_id <= hi


def get_reserved_area_indices(*, grain: int | None = None) -> frozenset[int]:
    """Reserved area indices for active grain; empty under grain 12."""
    if grain is None:
        from core.projection.area_math_grain import classify_area_math_grain

        grain = classify_area_math_grain()
    if grain == 12:
        return frozenset()
    _ensure_loaded()
    return frozenset(_reserved_areas) if _reserved_areas else frozenset()


def get_reserved_family_indices(*, grain: int | None = None) -> frozenset[int]:
    """Reserved family indices for active grain; empty under grain 12."""
    if grain is None:
        from core.projection.area_math_grain import classify_area_math_grain

        grain = classify_area_math_grain()
    if grain == 12:
        return frozenset()
    _ensure_loaded()
    return frozenset(_reserved_families) if _reserved_families else frozenset()
