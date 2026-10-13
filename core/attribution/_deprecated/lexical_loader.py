# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3 — Load Dict A (core star map) and Dict B (surface lex field).
Validates Spec 20: Dict A outputs side_id only (no family_id/area_id).
Reject startup if violations. No hot reload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Default assets root: hesperia root / assets
def _assets_root() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"


def _canonical_side_count() -> int:
    """Single source: invariant_catalog.TOTAL_SIDES."""
    try:
        from core.topology.invariant_catalog import TOTAL_SIDES
        return TOTAL_SIDES
    except ImportError:
        from invariant_catalog import TOTAL_SIDES
        return TOTAL_SIDES


def _canonical_side_set(n: int | None = None) -> set[int]:
    if n is None:
        n = _canonical_side_count()
    return set(range(n))


_ASSETS_REQUIRED_MSG = "Lexical assets missing. Run sync_curated_to_assets.sh from CLIENTS/hesperia."


def load_dict_a(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load A_CORE_STAR_MAP. Returns lemma -> list of {side_id, coefficient, map_code}. Fails if default assets path missing. Default: v0.4.1.1 (v0.4.1/v1 deprecated)."""
    default = _assets_root() / "A_CORE_STAR_MAP_v0_4_1_1.json"
    path = path or default
    if not path.exists():
        if path.resolve() == default.resolve():
            raise RuntimeError(_ASSETS_REQUIRED_MSG)
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, list)}


def load_dict_b(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load B_SURFACE_LEX_FIELD. Returns side_id (str) -> {canonical_lemma, aliases}. Fails if default assets path missing."""
    default = _assets_root() / "B_SURFACE_LEX_FIELD_v1.json"
    path = path or default
    if not path.exists():
        if path.resolve() == default.resolve():
            raise RuntimeError(_ASSETS_REQUIRED_MSG)
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}


def validate_spec20_dict_a(
    data: dict[str, list[dict[str, Any]]],
    canonical_max: int | None = None,
    side_id_format: str = "int",
) -> list[str]:
    """Spec 20: Dict A must output side_id only. No family_id, area_id. All side_id in canonical set; format per side_id_format."""
    if canonical_max is None:
        canonical_max = _canonical_side_count()
    errs = []
    canonical = _canonical_side_set(canonical_max)
    for lemma, entries in data.items():
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                continue
            for forbidden in ("family_id", "area_id", "family", "area"):
                if forbidden in e:
                    errs.append(f"Dict A '{lemma}'[{i}]: authority breach — must not contain {forbidden}")
            sid = e.get("side_id")
            if sid is not None:
                if side_id_format == "int":
                    try:
                        sid_int = int(sid)
                        if sid_int not in canonical:
                            errs.append(f"Dict A '{lemma}'[{i}]: side_id {sid} outside canonical [0, {canonical_max})")
                    except (TypeError, ValueError):
                        errs.append(f"Dict A '{lemma}'[{i}]: side_id must be integer (side_id_format=int)")
                else:
                    # string format: canonical set not defined here; caller must ensure consistency
                    pass
    return errs


def load_and_validate(
    assets_dir: Path | None = None,
    canonical_max: int | None = None,
    reject_on_violation: bool = True,
    side_id_format: str = "int",
) -> tuple[dict, dict, list[str]]:
    """
    Load Dict A and Dict B; validate Spec 20 and side_id_format. Returns (dict_a, dict_b, errors).
    side_id_format: "int" (canonical 0..N-1) or "string"; must match guard_config.
    If reject_on_violation and errors non-empty, raises RuntimeError.
    """
    root = assets_dir or _assets_root()
    a = load_dict_a(root / "A_CORE_STAR_MAP_v1.json")
    b = load_dict_b(root / "B_SURFACE_LEX_FIELD_v1.json")
    errs = validate_spec20_dict_a(a, canonical_max=canonical_max, side_id_format=side_id_format)
    if reject_on_violation and errs:
        raise RuntimeError("Spec 20 violation: " + "; ".join(errs[:5]))
    return a, b, errs
