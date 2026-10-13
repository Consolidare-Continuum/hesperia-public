# HESPERIA — TFP pole cascade audit (A11/A12 outcome contract, TFP-POLES-01)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Pole-cascade audit block for the TFP grain-12 outcome path.

Contract: colombo_research/hesperia/COLOMBO-POLES-OUTCOMES-CHAIN-2026-08-21.md
(operator-ratified 2026-08-21, brain `740a0034`; Grace triage
GRACE-TRIAGE-TFP-POLES-OUTCOME-SCHEMA-2026-08-21.md, row TFP-POLES-01).

A11/A12 are degree-5 hub areas on the icosahedral adjacency graph — they do
not border every other area at hop-1. This module makes that reachability
shape auditable per session: seed mass on the poles, the hop-1 delta on
their direct neighbors, the hop-2 delta on the areas poles only reach
indirectly, and the bipolar tension legs (A5<->A11, A6<->A12).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADJACENCY_PATH = _REPO_ROOT / "assets" / "topology" / "area_adjacency_matrix.json"

POLE_AREAS: tuple[str, str] = ("A11", "A12")
TENSION_LEGS: tuple[tuple[str, str], ...] = (("A5", "A11"), ("A6", "A12"))


def _area_id(index: int) -> str:
    return f"A{index + 1}"


@lru_cache(maxsize=1)
def _hop_sets() -> tuple[frozenset[str], frozenset[str]]:
    """Derive (hop1, hop2) area-id sets for the poles from the adjacency matrix."""
    data = json.loads(_ADJACENCY_PATH.read_text(encoding="utf-8"))
    matrix = data["matrix"]
    n = len(matrix)

    def neighbors(idx: int) -> set[int]:
        return {j for j in range(n) if matrix[idx][j]}

    pole_indices = {int(p[1:]) - 1 for p in POLE_AREAS}
    hop1_indices: set[int] = set()
    for p in pole_indices:
        hop1_indices |= neighbors(p)
    hop1_indices -= pole_indices

    hop2_indices: set[int] = set()
    for i in hop1_indices:
        hop2_indices |= neighbors(i)
    hop2_indices -= hop1_indices
    hop2_indices -= pole_indices

    hop1 = frozenset(_area_id(i) for i in hop1_indices)
    hop2 = frozenset(_area_id(i) for i in hop2_indices)
    return hop1, hop2


def _get(values: dict[str, float] | None, area_id: str) -> float:
    return float((values or {}).get(area_id, 0.0) or 0.0)


def build_pole_cascade(
    areas_raw: dict[str, float] | None,
    areas_inhibited: dict[str, float] | None,
) -> dict[str, Any]:
    """
    Build the seed -> hop-1 delta -> hop-2 delta -> tension audit block.

    ``areas_raw`` / ``areas_inhibited`` are the pre-/post-inhibition area
    vectors from ``build_invariant_activation`` (both keyed by the full
    TFP area_ids set). Values default to 0.0 for any missing area key, so
    this is safe to call even on a grain-10-pinned run (poles just read 0).
    """
    hop1, hop2 = _hop_sets()

    seed = {
        "raw": {p: _get(areas_raw, p) for p in POLE_AREAS},
        "inhibited": {p: _get(areas_inhibited, p) for p in POLE_AREAS},
    }
    hop1_delta = {
        a: _get(areas_inhibited, a) - _get(areas_raw, a) for a in sorted(hop1)
    }
    hop2_delta = {
        a: _get(areas_inhibited, a) - _get(areas_raw, a) for a in sorted(hop2)
    }
    tension = {
        f"{a}_{b}": {
            "raw": abs(_get(areas_raw, a) - _get(areas_raw, b)),
            "inhibited": abs(_get(areas_inhibited, a) - _get(areas_inhibited, b)),
        }
        for a, b in TENSION_LEGS
    }
    return {
        "poles": list(POLE_AREAS),
        "hop1_areas": sorted(hop1),
        "hop2_areas": sorted(hop2),
        "seed": seed,
        "hop1_delta": hop1_delta,
        "hop2_delta": hop2_delta,
        "tension": tension,
    }
