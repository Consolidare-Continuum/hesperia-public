# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-4 (37_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables: retrieval counts, family/area match, integrity, support index, gate.
Chunk: dict with bookId, familyId, chunkId; optional checksum_ok (default True).
When R_B/R_S empty: deterministic zeros/shortfall; gate fails when shortfall > MAX_SHORTFALL. Downstream: L5, L7, L8, L9.
"""

from __future__ import annotations

import math
import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput

# Chunk type: dict with keys bookId, familyId, chunkId; optional "checksum_ok" (default True)


def _area_of(family_id: int, F: int, A: int) -> int:
    return min(family_id // (F // A if A else 24), A - 1) if A else 0


def _jaccard(a: set, b: set) -> float:
    u = a | b
    if not u:
        return 1.0
    return len(a & b) / len(u)


def _entropy(counts: dict[int, int], F: int) -> float:
    total = sum(counts.values())
    if total <= 0 or F <= 1:
        return 0.0
    H = 0.0
    for n in counts.values():
        p = n / total
        if p > 0:
            H -= p * math.log(p)
    return H / (math.log(F) if F > 1 else 1.0)


def _gini(counts: list[int], eps: float = 1e-9) -> float:
    if not counts:
        return 0.0
    total = sum(counts)
    if total <= 0:
        return 0.0
    sorted_c = sorted(counts)
    n = len(sorted_c)
    return 1.0 - (2.0 / (n * total + eps)) * sum((n - i) * sorted_c[i] for i in range(n))


def compute_L4(
    l1_B: dict[str, Any],
    l1_S: dict[str, Any],
    hits_B: list[int],
    hits_S: list[int],
    R_B: list[dict[str, Any]],
    R_S: list[dict[str, Any]],
    F: int = 288,
    A: int = 12,
    RETRIEVAL_MODE_ID: str = "LEX_BM25_V1",
    TOP_K: int = 20,
    MAX_SHORTFALL: int = 2,
    MIN_SUPPORT: float = 0.30,
    MAX_DUP_BOOK_CONC: float = 0.70,
    eps: float = 1e-9,
) -> dict[str, Any]:
    """
    Compute Layer-4 25 variables (37_SPEC).
    Chunks: list of dicts with bookId, familyId, chunkId; optional checksum_ok (default True).
    """
    dominant_family_B = int(l1_B["DOMINANT_FAMILY_ID"])
    dominant_family_S = int(l1_S["DOMINANT_FAMILY_ID"])
    dominant_area_B = int(l1_B["DOMINANT_AREA_ID"])
    dominant_area_S = int(l1_S["DOMINANT_AREA_ID"])

    retrieved_B = len(R_B)
    retrieved_S = len(R_S)
    RETRIEVAL_SHORTFALL_BASELINE = max(0, TOP_K - retrieved_B)
    RETRIEVAL_SHORTFALL_SHADOW = max(0, TOP_K - retrieved_S)

    books_B = {c.get("bookId", str(i)) for i, c in enumerate(R_B)}
    books_S = {c.get("bookId", str(i)) for i, c in enumerate(R_S)}
    UNIQUE_BOOKS_BASELINE = len(books_B)
    UNIQUE_BOOKS_SHADOW = len(books_S)
    DUPLICATE_BOOK_RATIO_BASELINE = 1.0 - (UNIQUE_BOOKS_BASELINE / max(1, retrieved_B))
    DUPLICATE_BOOK_RATIO_SHADOW = 1.0 - (UNIQUE_BOOKS_SHADOW / max(1, retrieved_S))

    family_match_B = sum(1 for c in R_B if c.get("familyId") == dominant_family_B)
    FAMILY_MATCH_COUNT_BASELINE = family_match_B
    FAMILY_MATCH_RATIO_BASELINE = family_match_B / max(1, retrieved_B)

    area_match_B = sum(
        1 for c in R_B
        if _area_of(int(c.get("familyId", 0)), F, A) == dominant_area_B
    )
    AREA_MATCH_RATIO_BASELINE = area_match_B / max(1, retrieved_B)

    families_B = {int(c.get("familyId", 0)) for c in R_B}
    TOP_K_FAMILY_COVERAGE_BASELINE = len(families_B) / (F + eps)

    counts_B: dict[int, int] = {}
    for c in R_B:
        fid = int(c.get("familyId", 0))
        counts_B[fid] = counts_B.get(fid, 0) + 1
    EVIDENCE_ENTROPY_BASELINE = _entropy(counts_B, F)
    EVIDENCE_GINI_BASELINE = _gini(list(counts_B.values()), eps)

    weight_sum = 0.0
    aligned_sum = 0.0
    for r, c in enumerate(R_B):
        w = 1.0 / (r + 1)
        weight_sum += w
        if _area_of(int(c.get("familyId", 0)), F, A) == dominant_area_B:
            aligned_sum += w
    RANK_WEIGHTED_ALIGNMENT_BASELINE = (aligned_sum / weight_sum) if weight_sum > 0 else 0.0

    active_B = {f for f in range(min(len(hits_B), F)) if hits_B[f] > 0}
    HIT_EVIDENCE_OVERLAP_BASELINE = _jaccard(active_B, families_B)

    active_S = {f for f in range(min(len(hits_S), F)) if hits_S[f] > 0}
    families_S = {int(c.get("familyId", 0)) for c in R_S}
    HIT_EVIDENCE_OVERLAP_SHADOW = _jaccard(active_S, families_S)

    chunk_ids_B = {c.get("chunkId", str(i)) for i, c in enumerate(R_B)}
    chunk_ids_S = {c.get("chunkId", str(i)) for i, c in enumerate(R_S)}
    EVIDENCE_JACCARD_BS = _jaccard(chunk_ids_B, chunk_ids_S)
    BOOKSET_JACCARD_BS = _jaccard(books_B, books_S)
    EVIDENCE_SHIFT_SCORE = 1.0 - EVIDENCE_JACCARD_BS

    seen: set[str | int] = set()
    ok = 0
    for c in R_B + R_S:
        cid = c.get("chunkId", id(c))
        if cid not in seen:
            seen.add(cid)
            if c.get("checksum_ok", True):
                ok += 1
    INTEGRITY_CHECK_PASS_RATIO = (ok / len(seen)) if seen else 1.0

    EVIDENCE_SUPPORT_INDEX_BASELINE = (
        0.45 * FAMILY_MATCH_RATIO_BASELINE
        + 0.35 * AREA_MATCH_RATIO_BASELINE
        + 0.20 * HIT_EVIDENCE_OVERLAP_BASELINE
    )

    EVIDENCE_ACCEPTABILITY_GATE = (
        INTEGRITY_CHECK_PASS_RATIO == 1.0
        and RETRIEVAL_SHORTFALL_BASELINE <= MAX_SHORTFALL
        and EVIDENCE_SUPPORT_INDEX_BASELINE >= MIN_SUPPORT
        and DUPLICATE_BOOK_RATIO_BASELINE <= MAX_DUP_BOOK_CONC
    )

    return {
        "RETRIEVAL_MODE_ID": RETRIEVAL_MODE_ID,
        "TOP_K": TOP_K,
        "RETRIEVED_COUNT_BASELINE": retrieved_B,
        "RETRIEVED_COUNT_SHADOW": retrieved_S,
        "RETRIEVAL_SHORTFALL_BASELINE": RETRIEVAL_SHORTFALL_BASELINE,
        "RETRIEVAL_SHORTFALL_SHADOW": RETRIEVAL_SHORTFALL_SHADOW,
        "UNIQUE_BOOKS_BASELINE": UNIQUE_BOOKS_BASELINE,
        "UNIQUE_BOOKS_SHADOW": UNIQUE_BOOKS_SHADOW,
        "DUPLICATE_BOOK_RATIO_BASELINE": DUPLICATE_BOOK_RATIO_BASELINE,
        "DUPLICATE_BOOK_RATIO_SHADOW": DUPLICATE_BOOK_RATIO_SHADOW,
        "FAMILY_MATCH_COUNT_BASELINE": FAMILY_MATCH_COUNT_BASELINE,
        "FAMILY_MATCH_RATIO_BASELINE": FAMILY_MATCH_RATIO_BASELINE,
        "AREA_MATCH_RATIO_BASELINE": AREA_MATCH_RATIO_BASELINE,
        "TOP_K_FAMILY_COVERAGE_BASELINE": TOP_K_FAMILY_COVERAGE_BASELINE,
        "EVIDENCE_ENTROPY_BASELINE": EVIDENCE_ENTROPY_BASELINE,
        "EVIDENCE_GINI_BASELINE": EVIDENCE_GINI_BASELINE,
        "RANK_WEIGHTED_ALIGNMENT_BASELINE": RANK_WEIGHTED_ALIGNMENT_BASELINE,
        "HIT_EVIDENCE_OVERLAP_BASELINE": HIT_EVIDENCE_OVERLAP_BASELINE,
        "HIT_EVIDENCE_OVERLAP_SHADOW": HIT_EVIDENCE_OVERLAP_SHADOW,
        "EVIDENCE_JACCARD_BS": EVIDENCE_JACCARD_BS,
        "BOOKSET_JACCARD_BS": BOOKSET_JACCARD_BS,
        "EVIDENCE_SHIFT_SCORE": EVIDENCE_SHIFT_SCORE,
        "INTEGRITY_CHECK_PASS_RATIO": INTEGRITY_CHECK_PASS_RATIO,
        "EVIDENCE_SUPPORT_INDEX_BASELINE": EVIDENCE_SUPPORT_INDEX_BASELINE,
        "EVIDENCE_ACCEPTABILITY_GATE": EVIDENCE_ACCEPTABILITY_GATE,
    }


def run(input: LayerInput) -> LayerOutput:
    """Layer-4 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l1_B = layers.get(1)
    l1_S = meta.get("l1_shadow", l1_B)
    hits_B = meta.get("hits", [])
    hits_S = meta.get("hits_shadow", hits_B)
    R_B = meta.get("R_B", [])
    R_S = meta.get("R_S", [])
    if not l1_B:
        raise ValueError("Layer 4 requires layer 1 result in input.metadata['layers'][1]")
    F = int(meta.get("F", 288))
    A = int(meta.get("A", 12))
    defaults = meta.get("defaults", {})
    result = compute_L4(
        l1_B, l1_S, hits_B, hits_S, R_B, R_S,
        F=F,
        A=A,
        **{k: defaults.get(k) for k in ("RETRIEVAL_MODE_ID", "TOP_K", "MAX_SHORTFALL", "MIN_SUPPORT", "MAX_DUP_BOOK_CONC") if k in defaults},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=4,
        result=result,
        diagnostics={"layer_id": 4, "execution_time_ms": round(elapsed_ms, 6)},
    )
