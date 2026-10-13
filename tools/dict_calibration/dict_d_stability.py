# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W7 — leave-one-book-out / corpus-growth graph stability analysis.

Implements the metrics and thresholds frozen in
``docs/specs/ETHAN-CORE-D2-W7-SAMPLING-STABILITY-CONTRACT.md``.
"""
from __future__ import annotations

from typing import Any

from .dict_d_builder import build_dict_d

RANK_CORRELATION_MIN = 0.85
NPMI_DRIFT_MAX = 0.10
G2_DRIFT_RATIO_MAX = 0.50
TOP_K = 50
JACCARD_MIN = 0.60


def _pair_key(row: dict[str, Any]) -> tuple[str, str]:
    return (row["concept_id_a"], row["concept_id_b"])


def _spearman_rho(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation with average-rank tie handling; no scipy dependency."""
    n = len(x)
    if n < 2:
        return 1.0

    def _ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = _ranks(x), _ranks(y)
    mean_x, mean_y = sum(rx) / n, sum(ry) / n
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    var_x = sum((a - mean_x) ** 2 for a in rx)
    var_y = sum((b - mean_y) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return 1.0 if var_x == var_y else 0.0
    return cov / (var_x**0.5 * var_y**0.5)


def _top_k_pairs(rows: list[dict[str, Any]], k: int) -> frozenset[tuple[str, str]]:
    ranked = sorted(rows, key=lambda r: (-r["npmi"], _pair_key(r)))
    return frozenset(_pair_key(r) for r in ranked[:k])


def compare_rebuilds(baseline_rows: list[dict[str, Any]], perturbed_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare a perturbed Dict D rebuild against the baseline. Pure function, no I/O."""
    baseline_by_pair = {_pair_key(r): r for r in baseline_rows}
    perturbed_by_pair = {_pair_key(r): r for r in perturbed_rows}
    shared = sorted(set(baseline_by_pair) & set(perturbed_by_pair))
    appeared = sorted(set(perturbed_by_pair) - set(baseline_by_pair))
    disappeared = sorted(set(baseline_by_pair) - set(perturbed_by_pair))

    if shared:
        base_npmi = [baseline_by_pair[p]["npmi"] for p in shared]
        pert_npmi = [perturbed_by_pair[p]["npmi"] for p in shared]
        rank_correlation = _spearman_rho(base_npmi, pert_npmi)
        npmi_drift = sum(abs(a - b) for a, b in zip(base_npmi, pert_npmi)) / len(shared)
        g2_drift_ratio = sum(
            abs(perturbed_by_pair[p]["g2"] - baseline_by_pair[p]["g2"]) / max(baseline_by_pair[p]["g2"], 1.0)
            for p in shared
        ) / len(shared)
    else:
        rank_correlation = 1.0
        npmi_drift = 0.0
        g2_drift_ratio = 0.0

    top_baseline = _top_k_pairs(baseline_rows, TOP_K)
    top_perturbed = _top_k_pairs(perturbed_rows, TOP_K)
    union = top_baseline | top_perturbed
    jaccard = len(top_baseline & top_perturbed) / len(union) if union else 1.0

    passed = (
        rank_correlation >= RANK_CORRELATION_MIN
        and npmi_drift <= NPMI_DRIFT_MAX
        and g2_drift_ratio <= G2_DRIFT_RATIO_MAX
        and jaccard >= JACCARD_MIN
    )
    return {
        "n_shared_pairs": len(shared),
        "n_appeared": len(appeared),
        "n_disappeared": len(disappeared),
        "rank_correlation": rank_correlation,
        "npmi_drift": npmi_drift,
        "g2_drift_ratio": g2_drift_ratio,
        "top_k_jaccard": jaccard,
        "passed": passed,
        "thresholds": {
            "rank_correlation_min": RANK_CORRELATION_MIN,
            "npmi_drift_max": NPMI_DRIFT_MAX,
            "g2_drift_ratio_max": G2_DRIFT_RATIO_MAX,
            "jaccard_min": JACCARD_MIN,
        },
    }


def leave_one_book_out(
    resolved_export: dict[str, Any], candidate_dict_b: list[dict[str, Any]], *, evidence_floor: int
) -> dict[str, Any]:
    """Rebuild once per book with that book removed; compare each against the full-corpus baseline."""
    books = resolved_export["books"]
    if len(books) < 2:
        raise ValueError("leave-one-book-out requires at least 2 books")
    baseline = build_dict_d(resolved_export=resolved_export, candidate_dict_b=candidate_dict_b, evidence_floor=evidence_floor)
    per_book: dict[str, Any] = {}
    for i, book in enumerate(books):
        perturbed_export = {**resolved_export, "books": books[:i] + books[i + 1 :]}
        unresolved = [
            u for u in resolved_export["unresolved"] if u["book_id"] != book["book_id"]
        ]
        perturbed_export["unresolved"] = unresolved
        perturbed = build_dict_d(resolved_export=perturbed_export, candidate_dict_b=candidate_dict_b, evidence_floor=evidence_floor)
        per_book[book["book_id"]] = compare_rebuilds(baseline["rows"], perturbed["rows"])
    return {
        "baseline_summary": baseline["summary"],
        "removed_book_results": per_book,
        "all_passed": all(r["passed"] for r in per_book.values()),
    }


def corpus_growth(
    resolved_export: dict[str, Any],
    added_book: dict[str, Any],
    candidate_dict_b: list[dict[str, Any]],
    *,
    evidence_floor: int,
) -> dict[str, Any]:
    """Rebuild once with one extra book appended; compare against the baseline."""
    baseline = build_dict_d(resolved_export=resolved_export, candidate_dict_b=candidate_dict_b, evidence_floor=evidence_floor)
    grown_export = {**resolved_export, "books": [*resolved_export["books"], added_book]}
    grown = build_dict_d(resolved_export=grown_export, candidate_dict_b=candidate_dict_b, evidence_floor=evidence_floor)
    result = compare_rebuilds(baseline["rows"], grown["rows"])
    return {"baseline_summary": baseline["summary"], "growth_result": result}
