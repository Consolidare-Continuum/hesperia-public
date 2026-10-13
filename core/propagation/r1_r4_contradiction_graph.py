# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# Load R1-R4 contradiction graph C (Part B.5). Ref: r1_r4_contradiction_graph_v1_0.json
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_GRAPH_PATH = Path(__file__).resolve().parent / "r1_r4_contradiction_graph_v1_0.json"
CP_MAX = 0.25  # Part B.5: normalization for contradiction_pressure


def load_contradiction_graph(path: Path | None = None) -> dict[str, Any]:
    """Load C artifact (version, pairs)."""
    p = path if path is not None else _GRAPH_PATH
    if not p.exists():
        return {"version": "0", "pairs": []}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_pairs(graph: dict[str, Any] | None = None) -> list[tuple[int, int]]:
    """Return list of (i, j) with i < j. Graph may be from load_contradiction_graph()."""
    if graph is None:
        graph = load_contradiction_graph()
    pairs = graph.get("pairs", [])
    return [tuple(edge) for edge in pairs if len(edge) >= 2 and edge[0] < edge[1]]


def contradiction_pressure(p: list[float], pairs: list[tuple[int, int]] | None = None) -> float:
    """Part B.5: CP_raw = sum of p[i]*p[j] for (i,j) in C; return min(1, CP_raw / CP_MAX)."""
    if pairs is None:
        pairs = get_pairs()
    F = len(p)
    cp_raw = 0.0
    for i, j in pairs:
        if 0 <= i < F and 0 <= j < F:
            cp_raw += p[i] * p[j]
    return min(1.0, cp_raw / CP_MAX)
