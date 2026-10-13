# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Generic weighted-graph sparsification and degree-normalization toolkit: top-K neighbor
pruning, row-sum normalization with promotion pool, average-degree bumping/trimming,
deterministic weight jitter, and basic list statistics (median, percentile).

Graduated to core 2026-07-31 (was hesperia/extensions/triz/family_weights_sparsify_v052.py
— a real, generic algorithm toolkit buried inside an otherwise TRIZ-domain-specific
calibration file). Operates on opaque ``(str, str)`` edge keys and float weights; no
family/area/TRIZ semantics anywhere in this module. The TRIZ-specific weight-calibration
rules (``recalculated_pair_weight``, forbidden-weight nudging, locality-by-family-distance)
stayed in the original file, which now calls these functions.
"""

from __future__ import annotations

import zlib
from collections import defaultdict
from typing import Callable


def median_float(vals: list[float]) -> float:
    """Median of a float list; empty list returns 0.0."""
    if not vals:
        return 0.0
    s = sorted(vals)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def percentile_int(vals: list[int], pct: float = 0.95) -> int:
    """Percentile of an int list (nearest-rank); empty list returns 1. Result floored at 1."""
    if not vals:
        return 1
    s = sorted(vals)
    idx = min(len(s) - 1, int(pct * max(len(s) - 1, 1)))
    return max(1, s[idx])


def scale_by_membership(w: float, is_member: bool, *, non_member_scale: float = 0.5) -> float:
    """Scale w down by non_member_scale unless is_member is True."""
    return w if is_member else w * non_member_scale


def deterministic_jitter(
    key_a: str,
    key_b: str,
    w: float,
    *,
    min_weight: float,
    max_weight: float,
) -> float:
    """
    Break ties among identical weights with a small, stable (hash-keyed) perturbation.
    Deterministic for a fixed (key_a, key_b) pair.
    """
    z = zlib.adler32(f"{key_a}|{key_b}".encode("utf-8")) % 1000
    delta = z * 1e-5
    return min(max_weight, max(min_weight, w + delta))


def top_k_prune_symmetric(
    weights: dict[tuple[str, str], float],
    *,
    k: int,
) -> dict[tuple[str, str], float]:
    """
    Per node keep top-K neighbors by weight; edge survives if **either** endpoint ranks the
    other in its top-K (union / "at least one side cares"), then cap degree per node by
    trimming weakest incident edges to <=K.
    """
    nodes: set[str] = set()
    for a, b in weights:
        nodes.add(a)
        nodes.add(b)
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (a, b), w in weights.items():
        if w <= 0:
            continue
        adj[a].append((b, w))
        adj[b].append((a, w))
    topk: dict[str, set[str]] = {}
    for node in nodes:
        neigh = sorted(adj[node], key=lambda x: (-x[1], x[0]))
        topk[node] = {other for other, _ in neigh[:k]}
    cand: dict[tuple[str, str], float] = {}
    for (a, b), w in weights.items():
        if w <= 0:
            continue
        if b in topk.get(a, set()) or a in topk.get(b, set()):
            key = tuple(sorted((a, b)))
            cand[key] = max(cand.get(key, 0.0), w)

    def degree_excess(e_map: dict[tuple[str, str], float]) -> dict[str, int]:
        deg: dict[str, int] = defaultdict(int)
        for (x, y), ww in e_map.items():
            if ww <= 0:
                continue
            deg[x] += 1
            deg[y] += 1
        return {n: max(0, deg[n] - k) for n in nodes if deg[n] > k}

    out = dict(cand)
    for _ in range(len(nodes) * 3):
        ex = degree_excess(out)
        over = [n for n, x in ex.items() if x > 0]
        if not over:
            break
        n_drop = min(over, key=lambda z: z)
        inc = [(key, out[key]) for key in out if n_drop in key]
        if not inc:
            break
        weakest = min(inc, key=lambda t: (t[1], t[0]))
        del out[weakest[0]]
    return out


def row_sums(nodes: list[str], edges: dict[tuple[str, str], float]) -> dict[str, float]:
    """Sum of incident edge weights per node."""
    sums: dict[str, float] = defaultdict(float)
    for (a, b), w in edges.items():
        if w <= 0:
            continue
        sums[a] += w
        sums[b] += w
    return {n: sums.get(n, 0.0) for n in nodes}


def normalize_row_sums(
    edges: dict[tuple[str, str], float],
    nodes: list[str],
    *,
    promotion_pool: list[tuple[tuple[str, str], float]],
    sum_min: float,
    sum_max: float,
    max_promote: int,
    min_weight: float,
    max_weight: float,
    nudge_fn: Callable[[float], float] | None = None,
) -> dict[tuple[str, str], float]:
    """
    Scale down if any incident sum > sum_max.
    One pass: for nodes with sum in (0, sum_min), add up to max_promote edges from
    promotion_pool (strongest first). ``nudge_fn``, if given, post-processes each promoted
    weight (e.g. to steer clear of forbidden calibration values) before it's added.
    """
    e = dict(edges)
    pool = sorted(promotion_pool, key=lambda x: -x[1])
    pool_idx = 0

    for _ in range(32):
        rs = row_sums(nodes, e)
        mx = max(rs.values(), default=0.0)
        if mx > sum_max:
            f_down = sum_max / mx
            for k in list(e.keys()):
                e[k] = min(max_weight, max(0.0, e[k] * f_down))
            continue
        break

    rs = row_sums(nodes, e)
    under = [n for n in nodes if 0.0 < rs.get(n, 0.0) < sum_min]
    for n in under:
        added = 0
        while added < max_promote and pool_idx < len(pool):
            key, w0 = pool[pool_idx]
            pool_idx += 1
            a, b = key
            if n not in (a, b) or key in e:
                continue
            if w0 < min_weight:
                continue
            wv = nudge_fn(w0) if nudge_fn is not None else w0
            e[key] = min(max_weight, wv)
            added += 1
        rs2 = row_sums(nodes, e)
        if rs2.get(n, 0.0) > sum_max:
            f2 = sum_max / rs2[n]
            for k in list(e.keys()):
                a, b = k
                if a == n or b == n:
                    e[k] = min(max_weight, max(0.0, e[k] * f2))
    return e


def bump_avg_degree_from_pool(
    e: dict[tuple[str, str], float],
    nodes: list[str],
    pool: list[tuple[tuple[str, str], float]],
    *,
    target: float,
    min_weight: float,
    max_weight: float,
    max_add: int = 2500,
    nudge_fn: Callable[[float], float] | None = None,
) -> dict[tuple[str, str], float]:
    """If graph too sparse, add strongest pruned edges until avg degree target or cap."""
    n_v = len(nodes)
    if n_v == 0:
        return e

    def avg_deg() -> float:
        return (2.0 * len(e)) / n_v

    adds = 0
    for key, w0 in sorted(pool, key=lambda x: -x[1]):
        if avg_deg() >= target:
            break
        if adds >= max_add:
            break
        if key in e or w0 < min_weight:
            continue
        wv = nudge_fn(w0) if nudge_fn is not None else w0
        e[key] = min(max_weight, wv)
        adds += 1
    return e


def trim_avg_degree_high(
    e: dict[tuple[str, str], float],
    nodes: list[str],
    *,
    max_avg: float,
    max_rem: int = 8000,
) -> dict[tuple[str, str], float]:
    """If graph too dense, drop weakest edges until avg degree ceiling or cap."""
    n_v = len(nodes)
    if n_v == 0:
        return e
    rem = 0
    while (2.0 * len(e)) / n_v > max_avg and e and rem < max_rem:
        weakest = min(e, key=lambda k: e[k])
        del e[weakest]
        rem += 1
    return e


def graph_avg_degree(nodes: list[str], edges: dict[tuple[str, str], float]) -> float:
    """2|E|/|V|; 0.0 for an empty node set."""
    n_v = len(nodes)
    return (2.0 * len(edges)) / n_v if n_v else 0.0


def tiered_distance_multiplier(distance: int, tiers: dict[int, float], *, default: float) -> float:
    """Lookup a multiplier by integer distance tier; falls back to default for unlisted tiers."""
    return tiers.get(distance, default)


__all__ = [
    "median_float",
    "percentile_int",
    "scale_by_membership",
    "deterministic_jitter",
    "top_k_prune_symmetric",
    "row_sums",
    "normalize_row_sums",
    "bump_avg_degree_from_pool",
    "trim_avg_degree_high",
    "graph_avg_degree",
    "tiered_distance_multiplier",
]
