#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.6 — Dict A Integrity Audit (Phase 1).
Token-level variation, sentence-level raw vector dump, calibration statistics.
NO REBUILD. Decision tree: A = aggregation bug, B = artifact/softmax collapse, C = calibration failed.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.topology.invariant_catalog import TOTAL_FAMILIES

V06_DIR = REPO / "assets" / "lexicon" / "frozen" / "v0_5_0"
# Spec list (surface); if all OOV we also sample in-dict tokens for token-level variation
AUDIT_TOKENS_SPEC = [
    "altruism", "power", "trade", "ritual", "feedback",
    "authority", "capital", "identity", "competition", "cooperation",
]
SENTENCE_SAMPLES = [
    ("social_cohesion", "Altruism and trust strengthen mutual care within communities."),
    ("conflict_power", "Authority and control centralize institutional power."),
    ("technical_systems", "Feedback and optimization improve system efficiency."),
]
SIGMA_COLLAPSE_THRESHOLD = 1e-6


def load_dict_a_jsonl(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            t = rec.get("token", "").strip().lower()
            if t:
                out[t] = rec
    return out


def load_family_prior(path: Path) -> list[float]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    p = data.get("family_prior", [])
    if len(p) != TOTAL_FAMILIES:
        raise ValueError(f"family_prior length {len(p)}, expected {TOTAL_FAMILIES}")
    return p


def get_token_weights(token: str, dict_a: dict[str, dict], prior: list[float]) -> list[float]:
    """Full 288 weight vector for token (from dict topk+tail or prior for OOV)."""
    t = token.strip().lower()
    weights = [0.0] * TOTAL_FAMILIES
    if t not in dict_a:
        return list(prior)
    entry = dict_a[t]
    topk = entry.get("topk", [])
    topk_sum = 0.0
    for item in topk:
        fid = int(item.get("family_id", 0))
        w = float(item.get("w", 0))
        if 0 <= fid < TOTAL_FAMILIES:
            weights[fid] = w
            topk_sum += w
    tail_mass = 1.0 - topk_sum
    if tail_mass <= 0 or tail_mass < 1e-12:
        return weights
    topk_ids = {int(item.get("family_id", 0)) for item in topk if 0 <= int(item.get("family_id", 0)) < TOTAL_FAMILIES}
    sum_prior_excl = sum(prior[f] for f in range(TOTAL_FAMILIES) if f not in topk_ids)
    if sum_prior_excl <= 0:
        return weights
    for f in range(TOTAL_FAMILIES):
        if f not in topk_ids:
            weights[f] = tail_mass * (prior[f] / sum_prior_excl)
    return weights


def top_k_families(weights: list[float], k: int = 10) -> list[tuple[int, float]]:
    indexed = [(f, weights[f]) for f in range(TOTAL_FAMILIES)]
    indexed.sort(key=lambda x: -x[1])
    return indexed[:k]


def entropy(weights: list[float], eps: float = 1e-12) -> float:
    return -sum(w * math.log(w + eps) for w in weights if w > 0)


def margin_1_2(weights: list[float]) -> float:
    s = sorted(weights, reverse=True)
    return (s[0] - s[1]) if len(s) >= 2 else 0.0


def vec_checksum(vec: list[float]) -> str:
    blob = json.dumps([round(x, 10) for x in vec], separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Dict A v0.6 runtime integrity audit (Phase 1)")
    ap.add_argument("--v06-dir", type=Path, default=V06_DIR, help="lexicon/frozen/v06 directory")
    args = ap.parse_args()
    base = Path(args.v06_dir)
    dict_path = base / "dict_a_v06.jsonl"
    prior_path = base / "family_prior_v06.json"
    cal_path = base / "calibration_stats_v06.json"

    if not dict_path.exists():
        print(f"FAIL: Dict A not found: {dict_path}", file=sys.stderr)
        return 1
    if not prior_path.exists():
        print(f"FAIL: Family prior not found: {prior_path}", file=sys.stderr)
        return 1

    dict_a = load_dict_a_jsonl(dict_path)
    prior = load_family_prior(prior_path)

    fails: list[str] = []
    print("=" * 60)
    print("PHASE 1 — STRUCTURAL INTEGRITY AUDIT")
    print("=" * 60)

    # --- 1. Token-Level Variation Check ---
    print("\n--- 1. Token-Level Variation Check ---")
    # First: spec tokens (surface forms)
    spec_oov = [t for t in AUDIT_TOKENS_SPEC if t not in dict_a]
    spec_in = [t for t in AUDIT_TOKENS_SPEC if t in dict_a]
    if spec_oov:
        print(f"  Spec tokens {AUDIT_TOKENS_SPEC}: {len(spec_in)} in dict, {len(spec_oov)} OOV.")
    token_list = list(AUDIT_TOKENS_SPEC)
    if len(spec_in) < 3 and len(dict_a) >= 10:
        # Sample 10 in-dict tokens (spread) for variation check
        keys_sorted = sorted(dict_a.keys())
        step = max(1, len(keys_sorted) // 10)
        token_list = keys_sorted[::step][:10]
        print(f"  Using 10 in-dict tokens (spread) for variation: {token_list[:3]}...")
    token_results: list[tuple[str, list[tuple[int, float]], float, float]] = []
    for t in token_list:
        w = get_token_weights(t, dict_a, prior)
        top10 = top_k_families(w, 10)
        m12 = margin_1_2(w)
        ent = entropy(w)
        token_results.append((t, top10, m12, ent))
        in_dict = " (in dict)" if t in dict_a else " (OOV)"
        print(f"\nToken: {t}{in_dict}")
        print(f"  margin_1_2: {m12:.6f}  entropy: {ent:.4f}")
        print(f"  top 10 families: {[(f, round(w, 4)) for f, w in top10]}")

    # FAIL: in-dict token outputs identical or nearly identical (Case B)
    in_dict_results = [(t, r) for t, r in zip(token_list, token_results) if t in dict_a]
    if len(in_dict_results) >= 2:
        first_top10 = tuple((f, round(w, 6)) for f, w in in_dict_results[0][1][1])
        first_ent = in_dict_results[0][1][3]
        all_same = all(
            tuple((f, round(w, 6)) for f, w in r[1]) == first_top10 and abs(r[3] - first_ent) < 1e-6
            for _, r in in_dict_results[1:]
        )
        if all_same:
            fails.append("Token-level: in-dict outputs identical or nearly identical → Dict A artifact corrupted or softmax collapse (Case B).")
    elif len(spec_in) == 0 and len(token_results) >= 2:
        # All spec tokens OOV → identical (prior); verdict is vocabulary mismatch
        fails.append("Token-level: all spec tokens OOV → identical prior. Runtime tokenize yields surface forms; dict has structural keys (vocabulary mismatch).")

    # --- 2. Sentence-Level Raw Vector Dump ---
    print("\n--- 2. Sentence-Level Raw Vector Dump ---")
    from core.attribution.attribution_shared import normalize, tokenize
    sentence_vectors: list[tuple[str, str, list[float]]] = []
    for domain, text in SENTENCE_SAMPLES:
        norm = normalize(text, cap=10_000)
        tokens = tokenize(norm)
        if not tokens:
            vec = list(prior)
        else:
            acc = [0.0] * TOTAL_FAMILIES
            for t in tokens:
                w = get_token_weights(t, dict_a, prior)
                for f in range(TOTAL_FAMILIES):
                    acc[f] += w[f]
            n = len(tokens)
            vec = [acc[f] / n for f in range(TOTAL_FAMILIES)]
        sentence_vectors.append((domain, text, vec))
        checksum = vec_checksum(vec)
        top10 = top_k_families(vec, 10)
        print(f"\nDomain: {domain}")
        print(f"  Sentence: {text[:60]}...")
        print(f"  288-vector checksum: {checksum}")
        print(f"  top 10 families: {[(f, round(w, 6)) for f, w in top10]}")

    # FAIL: sentence vectors identical
    if len(sentence_vectors) >= 2:
        c0 = vec_checksum(sentence_vectors[0][2])
        all_same_sent = all(vec_checksum(v[2]) == c0 for v in sentence_vectors[1:])
        if all_same_sent:
            fails.append("Sentence-level: vectors identical. If tokens are all OOV → vocabulary mismatch (build keys vs tokenize surface). Else → aggregation bug (Case A).")

    # --- 3. Calibration Statistics Dump ---
    print("\n--- 3. Calibration Statistics Dump ---")
    if not cal_path.exists():
        print("  calibration_stats_v06.json not found. Run build with --save-calibration-stats.")
        print("  SKIP: Cannot evaluate σ_f collapse (Case C) without build-time stats.")
    else:
        with open(cal_path, encoding="utf-8") as f:
            cal = json.load(f)
        mu_f = cal.get("mu_f", [])
        sigma_f = cal.get("sigma_f", [])
        if len(sigma_f) != TOTAL_FAMILIES or len(mu_f) != TOTAL_FAMILIES:
            print(f"  Invalid calibration_stats: mu_f len={len(mu_f)}, sigma_f len={len(sigma_f)}")
        else:
            min_sig = min(sigma_f)
            max_sig = max(sigma_f)
            mean_sig = sum(sigma_f) / len(sigma_f)
            n_collapsed = sum(1 for s in sigma_f if s < SIGMA_COLLAPSE_THRESHOLD)
            print(f"  min σ_f: {min_sig:.6e}")
            print(f"  max σ_f: {max_sig:.6e}")
            print(f"  mean σ_f: {mean_sig:.6e}")
            print(f"  number of σ_f < 1e-6: {n_collapsed}")
            # histogram of μ_f (e.g. 10 bins)
            if mu_f:
                lo, hi = min(mu_f), max(mu_f)
                bins = 10
                step = (hi - lo) / bins if hi > lo else 1
                hist = [0] * bins
                for m in mu_f:
                    i = min(int((m - lo) / step) if step > 0 else 0, bins - 1)
                    hist[i] += 1
                print(f"  histogram μ_f (10 bins): {hist}")
            if n_collapsed > 0:
                fails.append("Calibration: σ_f collapse exists → calibration broken (Case C).")

    # --- Decision tree ---
    print("\n" + "=" * 60)
    print("DECISION TREE")
    print("=" * 60)
    if not fails:
        print("No hard FAIL conditions met. Token and sentence vectors vary.")
        print("If dominant_family still collapses in run, check aggregation (mean then normalize once).")
        return 0
    for f in fails:
        print(f"FAIL: {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
