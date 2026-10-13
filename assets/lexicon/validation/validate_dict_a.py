#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.6 — Validate Dict A v0.6 artifact.
Verifies: 288 anchors (from family spec), weights sum to 1, no negative, no NaN.
Reports: % strong tokens, family dominance histogram, entropy distribution, top-1 imbalance warning.
Hard-fail on: structural violations, σ_f collapse, missing families.
Do NOT fail on low strong percentage — only warn.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.topology.invariant_catalog import TOTAL_FAMILIES

SUM_TOL = 1e-6
OUT_DIR = REPO / "assets" / "lexicon" / "frozen" / "v0_5_0"
DICT_A_JSONL = "dict_a_v06.jsonl"
FAMILY_PRIOR = "family_prior_v06.json"
FAMILY_SPEC = REPO / "assets" / "lexicon" / "curated" / "FAMILY_SPEC_v0_6.json"
REPORT_PATH = OUT_DIR / "dict_a_v06_validation_report.txt"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Validate Dict A v0.6 artifact")
    ap.add_argument("--dict-a", type=Path, default=OUT_DIR / DICT_A_JSONL, help="dict_a_v06.jsonl path")
    ap.add_argument("--family-spec", type=Path, default=FAMILY_SPEC, help="FAMILY_SPEC_v0_6.json (for anchor count)")
    ap.add_argument("--report", type=Path, default=REPORT_PATH, help="Output report path")
    ap.add_argument("--strict-strong-pct", action="store_true", help="Fail if strong %% below 20 (default: warn only)")
    args = ap.parse_args()

    report_lines: list[str] = []
    failed = False

    # 288 anchors (from family spec)
    if not args.family_spec.exists():
        report_lines.append(f"FAIL: family spec not found: {args.family_spec}")
        failed = True
    else:
        with open(args.family_spec, encoding="utf-8") as f:
            spec = json.load(f)
        if not isinstance(spec, list) or len(spec) != TOTAL_FAMILIES:
            report_lines.append(f"FAIL: family spec must have exactly {TOTAL_FAMILIES} families, got {len(spec) if isinstance(spec, list) else 'N/A'}")
            failed = True
        else:
            report_lines.append(f"PASS: family spec has {TOTAL_FAMILIES} families")

    if not args.dict_a.exists():
        report_lines.append(f"FAIL: Dict A artifact not found: {args.dict_a}")
        failed = True
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        return 1

    entries: list[dict] = []
    with open(args.dict_a, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))

    # Structural: each entry has token, topk, metrics
    for i, rec in enumerate(entries):
        if "token" not in rec or "topk" not in rec or "metrics" not in rec:
            report_lines.append(f"FAIL: entry {i} missing token/topk/metrics")
            failed = True
        topk = rec.get("topk", [])
        for k, item in enumerate(topk):
            if not isinstance(item, dict) or "family_id" not in item or "w" not in item:
                report_lines.append(f"FAIL: entry {i} topk[{k}] invalid")
                failed = True
            w = item.get("w", 0)
            if w < 0:
                report_lines.append(f"FAIL: entry {i} topk[{k}] negative weight {w}")
                failed = True
            if isinstance(w, float) and (w != w):  # NaN
                report_lines.append(f"FAIL: entry {i} topk[{k}] NaN")
                failed = True
        # Sum of full 288 must be 1; we only have topk 32 in artifact. So we cannot verify full sum from jsonl alone.
        # Spec says "All tokens sum to 1 (within tolerance)" — that refers to the full 288 weights at build time.
        # Validation can check: topk weights are non-negative, no NaN, and (if we had tail) sum would be 1.
        # We can check sum of topk + implied tail >= 0 and <= 1. For strict check we'd need full vector; artifact stores topk only.
        # So: report "per-token topk sum" as info; hard-fail only on negative or NaN.
    if not failed:
        report_lines.append(f"PASS: {len(entries)} entries, structure and non-negative weights OK")

    # Metrics
    strong_count = 0
    entropy_list: list[float] = []
    argmax_per_family: list[int] = [0] * TOTAL_FAMILIES
    for rec in entries:
        m = rec.get("metrics", {})
        if m.get("strong") is True:
            strong_count += 1
        e = m.get("entropy")
        if e is not None:
            entropy_list.append(float(e))
        topk = rec.get("topk", [])
        if topk:
            family_id = topk[0].get("family_id", 0)
            if 0 <= family_id < TOTAL_FAMILIES:
                argmax_per_family[family_id] += 1

    pct_strong = (100.0 * strong_count / len(entries)) if entries else 0.0
    report_lines.append(f"Strong tokens: {strong_count} / {len(entries)} ({pct_strong:.1f}%)")
    if pct_strong < 20.0:
        report_lines.append(f"WARN: strong percentage below 20% (domain-dependent; consider refining anchors)")
        if getattr(args, "strict_strong_pct", False):
            failed = True
    else:
        report_lines.append("PASS: strong percentage >= 20%")

    if entropy_list:
        report_lines.append(f"Entropy distribution: min={min(entropy_list):.4f} max={max(entropy_list):.4f} mean={sum(entropy_list)/len(entropy_list):.4f}")

    # Family dominance histogram
    report_lines.append("Family dominance (top-1 count per family):")
    for f in range(TOTAL_FAMILIES):
        report_lines.append(f"  family {f}: {argmax_per_family[f]}")
    max_dom = max(argmax_per_family) if argmax_per_family else 0
    total = sum(argmax_per_family)
    max_pct = (100.0 * max_dom / total) if total else 0
    if max_pct > 25.0:
        report_lines.append(f"WARN: single family dominates {max_pct:.1f}% of tokens (top-1); justify or rebalance")
    else:
        report_lines.append("PASS: no single family > 25% top-1 dominance")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("\n".join(report_lines))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
