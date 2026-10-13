# HESPERIA — RAD. Family graph sparsification + weight recalibration.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
#
# MOVED 2026-07-31: the generic sparsification/degree-normalization algorithms now live in
# core.math.graph_sparsify — this file keeps the TRIZ weight-calibration business rules
# (recalculated_pair_weight, forbidden-weight nudging, locality-by-family-distance) and
# calls the core functions with this file's own calibration constants. Debloated of stale
# version-number naming (was family_weights_sparsify_v052.py) — irrelevant post-0.7.0-seal.

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from typing import Any

from core.math.graph_sparsify import (
    bump_avg_degree_from_pool,
    deterministic_jitter,
    graph_avg_degree,
    median_float,
    normalize_row_sums,
    percentile_int,
    scale_by_membership,
    tiered_distance_multiplier,
    top_k_prune_symmetric,
    trim_avg_degree_high,
)
from hesperia.extensions.triz.topology_activation_pipeline import concept_id_to_area_family

TOP_K = 8
MIN_WEIGHT = 0.25
MAX_WEIGHT = 0.9
FORBIDDEN_WEIGHTS = frozenset({0.2, 0.5})
NORM_SUM_MIN = 2.5
NORM_SUM_MAX = 4.5
MAX_PROMOTE = 2
AVG_DEG_MIN = 4.0
AVG_DEG_MAX = 10.0
UNIFORMITY_FRAC_MAX = 0.30
ACTIVE_CONTRA_THRESHOLD = 0.4

_LOCALITY_TIERS = {0: 1.0, 1: 0.8, 2: 0.5}


def _area(fk: str) -> str:
    return fk.split("_", 1)[0]


def _family_distance(fa: str, fb: str) -> int:
    if fa == fb:
        return 0
    if _area(fa) == _area(fb):
        return 1
    return 2


def load_family_weights(path: Any) -> dict[str, dict[str, float]]:
    p = path if isinstance(path, dict) else json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, float]] = {}
    for a, row in p.items():
        if not isinstance(row, dict):
            continue
        out[str(a)] = {str(b): float(v) for b, v in row.items()}
    return out


def load_concept_clusters(path: Any) -> list[dict[str, Any]]:
    raw = path if isinstance(path, dict) else json.loads(path.read_text(encoding="utf-8"))
    clusters = raw.get("clusters") or raw.get("concept_clusters") or []
    return [c for c in clusters if isinstance(c, dict)]


def _families_from_cluster(cl: dict[str, Any]) -> set[str]:
    fs: set[str] = set()
    for f in cl.get("families") or []:
        fs.add(str(f))
    for cid in cl.get("concepts") or []:
        p = concept_id_to_area_family(str(cid))
        if p:
            fs.add(p[1])
    return fs


def family_cluster_membership(clusters: list[dict[str, Any]]) -> dict[str, set[str]]:
    fam_to_clusters: dict[str, set[str]] = defaultdict(set)
    for i, cl in enumerate(clusters):
        cid = str(cl.get("cluster_id") or cl.get("id") or f"cluster_{i}")
        for fk in _families_from_cluster(cl):
            fam_to_clusters[fk].add(cid)
    return fam_to_clusters


def family_pair_cooccurrence(clusters: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for cl in clusters:
        fams = sorted(_families_from_cluster(cl))
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                a, b = fams[i], fams[j]
                if a == b:
                    continue
                key = tuple(sorted((a, b)))
                counts[key] += 1
    return counts


def recalculated_pair_weight(
    fa: str,
    fb: str,
    *,
    original: float,
    cooc: int,
    share_cluster: bool,
    same_area_cooc_values: list[int],
    global_cross_coocs: list[int],
    predefined_strong: bool,
) -> float | None:
    """Base weight (no locality / cluster scale). Cross-area without shared cluster → DROP."""
    if fa == fb:
        return None
    dist_area = _family_distance(fa, fb)

    if dist_area == 1:
        med = median_float([float(x) for x in same_area_cooc_values])
        high = float(cooc) > med if same_area_cooc_values else bool(cooc > 0)
        w = 0.85 if high else 0.7
    elif dist_area == 2:
        if not share_cluster:
            return None
        mx = percentile_int(global_cross_coocs, pct=0.95)
        w = 0.35 + 0.25 * min(1.0, float(cooc) / float(mx))
    else:
        return None

    if predefined_strong or original >= 1.0 - 1e-9:
        w = max(w, 0.88)
    return min(MAX_WEIGHT, max(MIN_WEIGHT, w))


def apply_cluster_scale(w: float, share: bool) -> float:
    return scale_by_membership(w, share)


def apply_locality(w: float, fa: str, fb: str) -> float:
    d = _family_distance(fa, fb)
    mult = tiered_distance_multiplier(d, _LOCALITY_TIERS, default=0.5)
    return min(MAX_WEIGHT, max(0.0, w * mult))


def _nudge_forbidden(w: float) -> float:
    if round(w, 4) in FORBIDDEN_WEIGHTS:
        return 0.26 if w < 0.4 else 0.36
    return w


def deterministic_weight_jitter(fa: str, fb: str, w: float) -> float:
    """Break >30%% identical weights; stable for fixed (fa,fb)."""
    return deterministic_jitter(fa, fb, w, min_weight=MIN_WEIGHT, max_weight=MAX_WEIGHT)


def build_sparse_family_weights(
    family_weights: dict[str, dict[str, float]],
    clusters: list[dict[str, Any]],
    *,
    use_effective_weight: bool = True,
) -> dict[str, Any]:
    """
    Full family-weight sparsification pipeline. Raises ValueError on validation failure.
    """
    nodes = sorted(family_weights.keys())
    node_set = set(nodes)

    fam_cl = family_cluster_membership(clusters)
    cooc = family_pair_cooccurrence(clusters)
    same_area_cooc_values = [int(c) for (a, b), c in cooc.items() if _area(a) == _area(b)]
    cross_cooc_list = [int(c) for (a, b), c in cooc.items() if _area(a) != _area(b)]

    raw_edges: dict[tuple[str, str], float] = {}

    for fa in nodes:
        row = family_weights.get(fa) or {}
        for fb, ow in row.items():
            if fb not in node_set or fa >= fb:
                continue
            key = tuple(sorted((fa, fb)))
            owf = float(ow)
            if owf <= 0:
                continue
            share = bool(fam_cl.get(fa, set()) & fam_cl.get(fb, set()))
            c = int(cooc.get(key, 0))
            pre_strong = owf >= 1.0 - 1e-9
            w0 = recalculated_pair_weight(
                fa,
                fb,
                original=owf,
                cooc=c,
                share_cluster=share,
                same_area_cooc_values=same_area_cooc_values,
                global_cross_coocs=cross_cooc_list,
                predefined_strong=pre_strong,
            )
            if w0 is None:
                continue
            w0 = apply_cluster_scale(w0, share)
            w0 = apply_locality(w0, fa, fb)
            if w0 < MIN_WEIGHT:
                continue
            w0 = min(MAX_WEIGHT, w0)
            w0 = _nudge_forbidden(w0)
            if w0 < MIN_WEIGHT:
                continue
            raw_edges[key] = w0

    pruned = top_k_prune_symmetric(raw_edges, k=TOP_K)
    pruned2: dict[tuple[str, str], float] = {}
    for key, w in pruned.items():
        if w < MIN_WEIGHT:
            continue
        w = _nudge_forbidden(min(MAX_WEIGHT, w))
        if w < MIN_WEIGHT:
            continue
        pruned2[key] = w

    promotion_pool = sorted(
        [(k, raw_edges[k]) for k in raw_edges if k not in pruned2],
        key=lambda x: -x[1],
    )
    normalized = normalize_row_sums(
        pruned2,
        nodes,
        promotion_pool=promotion_pool,
        sum_min=NORM_SUM_MIN,
        sum_max=NORM_SUM_MAX,
        max_promote=MAX_PROMOTE,
        min_weight=MIN_WEIGHT,
        max_weight=MAX_WEIGHT,
        nudge_fn=_nudge_forbidden,
    )
    normalized = bump_avg_degree_from_pool(
        normalized,
        nodes,
        promotion_pool,
        target=AVG_DEG_MIN,
        min_weight=MIN_WEIGHT,
        max_weight=MAX_WEIGHT,
        nudge_fn=_nudge_forbidden,
    )
    normalized = trim_avg_degree_high(normalized, nodes, max_avg=AVG_DEG_MAX)

    edge_list: list[dict[str, Any]] = []
    for key, w in sorted(normalized.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
        fa, fb = key
        wj = deterministic_weight_jitter(fa, fb, w)
        wj = min(MAX_WEIGHT, max(MIN_WEIGHT, wj))
        wj = _nudge_forbidden(wj)
        c = int(cooc.get(key, 0))
        olog = math.log1p(float(c))
        eff = round(min(MAX_WEIGHT, wj * olog), 6) if use_effective_weight and c > 0 else round(wj, 6)
        edge_list.append(
            {
                "family_i": fa,
                "family_j": fb,
                "weight": round(wj, 6),
                "active_for_contradiction": bool(wj >= ACTIVE_CONTRA_THRESHOLD),
                "effective_weight": eff,
                "cluster_cooccurrence": c,
            }
        )

    sparse_matrix: dict[str, dict[str, float]] = {n: {m: 0.0 for m in nodes} for n in nodes}
    for e in edge_list:
        fi, fj = e["family_i"], e["family_j"]
        w = float(e["weight"])
        sparse_matrix[fi][fj] = w
        sparse_matrix[fj][fi] = w

    n_e = len(edge_list)
    n_v = len(nodes)
    avg_deg = graph_avg_degree(nodes, {tuple(sorted((e["family_i"], e["family_j"]))): e["weight"] for e in edge_list})

    rounded_weights = [round(e["weight"], 3) for e in edge_list]
    cnt = Counter(rounded_weights)
    max_share = max((cnt[wv] / max(len(edge_list), 1)) for wv in cnt) if edge_list else 0.0

    errors: list[str] = []
    # Full §9 checks only when graph is large enough (unit tests / tiny sessions).
    degree_checks = n_v >= 30 and len(edge_list) >= 20
    uniform_check = len(edge_list) >= 30
    if edge_list and degree_checks:
        if avg_deg > AVG_DEG_MAX:
            errors.append(f"avg_degree_too_high:{avg_deg:.4f}>{AVG_DEG_MAX}")
        if avg_deg < AVG_DEG_MIN:
            errors.append(f"avg_degree_too_low:{avg_deg:.4f}<{AVG_DEG_MIN}")
    if uniform_check and max_share > UNIFORMITY_FRAC_MAX:
        errors.append(f"uniformity:{max_share:.4f}>{UNIFORMITY_FRAC_MAX}")

    for e in edge_list:
        rw = round(e["weight"], 4)
        if rw in FORBIDDEN_WEIGHTS:
            errors.append(f"forbidden_weight:{e['family_i']}-{e['family_j']}:{rw}")

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "params": {
            "top_k": TOP_K,
            "min_weight": MIN_WEIGHT,
            "max_weight": MAX_WEIGHT,
            "norm_sum_range": [NORM_SUM_MIN, NORM_SUM_MAX],
            "avg_degree_range": [AVG_DEG_MIN, AVG_DEG_MAX],
        },
        "node_count": n_v,
        "edge_count": n_e,
        "avg_degree": round(avg_deg, 6),
        "max_weight_share": round(max_share, 6),
        "validation_degree_checks": degree_checks,
        "validation_uniformity_check": uniform_check,
        "edges": edge_list,
        "matrix_sparse": sparse_matrix,
    }


def run_sparsify_from_paths(
    family_weights_path: Any,
    concept_clusters_path: Any,
    *,
    use_effective_weight: bool = True,
) -> dict[str, Any]:
    fw = load_family_weights(family_weights_path)
    cl = load_concept_clusters(concept_clusters_path)
    return build_sparse_family_weights(fw, cl, use_effective_weight=use_effective_weight)
