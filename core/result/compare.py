"""Cross-run comparability layer for canonical results."""

from __future__ import annotations

import math
from typing import Any


def _l2(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(n)))


def compare(result_a: dict[str, Any], result_b: dict[str, Any]) -> dict[str, Any]:
    return {
        "vector_distance_area": _l2(result_a["area_vector"], result_b["area_vector"]),
        "vector_distance_family": _l2(result_a["family_vector"], result_b["family_vector"]),
        "dominant_match": (
            int(result_a["dominant_area"]) == int(result_b["dominant_area"])
            and int(result_a["dominant_family"]) == int(result_b["dominant_family"])
        ),
        "tension_delta": abs(float(result_a["tension"]) - float(result_b["tension"])),
    }

