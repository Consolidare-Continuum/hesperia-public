"""Resolve conflicting module signals into final outputs."""

from __future__ import annotations

from typing import Any


def resolve_scores(
    vectors: list[tuple[dict[str, float], float, int]],
    *,
    strategy: str = "weighted_merge",
) -> dict[str, float]:
    if strategy == "exclusive":
        if not vectors:
            return {}
        top = sorted(vectors, key=lambda x: (x[2], x[1]), reverse=True)[0]
        return dict(top[0])
    if strategy == "priority":
        out: dict[str, float] = {}
        for vec, _weight, _prio in sorted(vectors, key=lambda x: x[2], reverse=True):
            for k, v in vec.items():
                out.setdefault(str(k), float(v))
        return out
    out: dict[str, float] = {}
    for vec, weight, _prio in vectors:
        for k, v in vec.items():
            out[str(k)] = out.get(str(k), 0.0) + float(v) * float(weight)
    return out


def merge_module_payloads(payloads: list[tuple[dict[str, Any], float, int]], strategy: str) -> tuple[dict[str, float], dict[str, float]]:
    family_vectors = [(dict(p.get("family_scores") or {}), w, pr) for p, w, pr in payloads]
    area_vectors = [(dict(p.get("area_scores") or {}), w, pr) for p, w, pr in payloads]
    return resolve_scores(family_vectors, strategy=strategy), resolve_scores(area_vectors, strategy=strategy)

