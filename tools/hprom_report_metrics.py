#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""HPROM REPORT-mode metrics: DLCR on Russian sample lines per sealed calibration version."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.engine.lexical_concept.pipeline import run_dlcr_pipeline


def _shannon_entropy(weights: dict[str, float]) -> float:
    tot = sum(max(0.0, float(v)) for v in weights.values())
    if tot <= 0:
        return 0.0
    h = 0.0
    for v in weights.values():
        p = max(0.0, float(v)) / tot
        if p > 0:
            h -= p * math.log(p + 1e-15, 2)
    return h


def _coverage_chars(canonical: str, span_outputs: list[dict[str, Any]]) -> float:
    """Char mask from ``token_span`` [start,end) on canonical (DLCR resolutions)."""
    if not canonical:
        return 1.0
    n = len(canonical)
    mask = [0] * n
    for s in span_outputs:
        ts = s.get("token_span")
        if isinstance(ts, (list, tuple)) and len(ts) >= 2:
            ss, se = int(ts[0]), int(ts[1])
            for j in range(max(0, ss), min(n, se)):
                mask[j] = 1
    return sum(mask) / max(1, n)


def _blocked_token_ratio(canonical: str, c_char_spans: list[tuple[int, int]]) -> float:
    toks = list(re.finditer(r"\S+", canonical))
    if not toks:
        return 0.0
    n_blk = 0
    for m in toks:
        ts, te = m.start(), m.end()
        if any(ss < te and ts < se for ss, se in c_char_spans):
            n_blk += 1
    return n_blk / len(toks)


def _load_ru_samples(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def evaluate_version(version: str, texts: list[str], *, mode: str = "clinical_speech") -> dict[str, Any]:
    os.environ["HESPERIA_CALIB_DICT_VERSION"] = version
    agg_cw: dict[str, float] = defaultdict(float)
    agg_fam: dict[str, float] = defaultdict(float)
    total_acc = 0
    total_rej = 0
    unmapped_ratios: list[float] = []
    n_c_res = 0
    n_res = 0
    blocked_ratios: list[float] = []

    for t in texts:
        out = run_dlcr_pipeline(t, repo_root=REPO, mode=mode)
        for k, v in (out.get("concept_weights") or {}).items():
            agg_cw[k] += float(v)
        for k, v in (out.get("family_activation") or {}).items():
            agg_fam[k] += float(v)
        total_acc += int(out.get("lexical_hits_accepted") or 0)
        total_rej += int(out.get("lexical_hits_rejected") or 0)
        canon = str(out.get("canonical_text") or "")
        spans = list(out.get("span_resolutions") or [])
        cov = _coverage_chars(canon, spans)
        unmapped_ratios.append(1.0 - cov)
        for s in spans:
            n_res += 1
            if str(s.get("source_dict") or "").upper() == "C":
                n_c_res += 1
        c_spans: list[tuple[int, int]] = []
        for s in spans:
            if str(s.get("source_dict") or "").upper() != "C":
                continue
            ts = s.get("token_span")
            if isinstance(ts, (list, tuple)) and len(ts) >= 2:
                c_spans.append((int(ts[0]), int(ts[1])))
        blocked_ratios.append(_blocked_token_ratio(canon, c_spans))

    noise_denom = max(1, total_acc + total_rej)
    phrase_hit = round(n_c_res / max(1, n_res), 6) if n_res else 0.0
    concept_activation_from_c_ratio = phrase_hit
    token_contribution_ratio = round(1.0 - phrase_hit, 6) if n_res else 1.0

    return {
        "concept_activation": {k: round(v, 6) for k, v in sorted(agg_cw.items())},
        "concept_entropy": round(_shannon_entropy(dict(agg_cw)), 6),
        "family_activation": {k: round(v, 6) for k, v in sorted(agg_fam.items())},
        "family_balance_gini_stub": round(
            1.0 - sum(1 for _ in agg_fam) / max(1, len(agg_fam)), 6
        ),
        "noise_ratio": round(total_rej / noise_denom, 6),
        "unmapped_lexical_pct_mean": round(
            100.0 * (sum(unmapped_ratios) / max(1, len(unmapped_ratios))), 4
        ),
        "phrase_hit_ratio": phrase_hit,
        "token_contribution_ratio": token_contribution_ratio,
        "concept_activation_from_c_ratio": concept_activation_from_c_ratio,
        "blocked_token_ratio_est": round(
            sum(blocked_ratios) / max(1, len(blocked_ratios)), 6
        ),
        "used_concepts_count": len(agg_cw),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit HPROM REPORT JSON for calibration versions.")
    ap.add_argument(
        "--dataset",
        type=Path,
        default=REPO / "tests" / "fixtures" / "tfp_calibration" / "sample_inputs_ru.txt",
    )
    ap.add_argument("--out", type=Path, default=REPO / "outputs" / "reports" / "hprom_03_report_eval.json")
    ap.add_argument("--run-label", default="hprom_03_report_eval_v6", help="JSON run id")
    ap.add_argument(
        "--versions",
        default="v0_6_0_clr_v052_2,v0_6_0_clr_v052_3,v0_6_0_clr_v052_4,v0_6_0_clr_v052_5",
        help="Comma-separated HESPERIA_CALIB_DICT_VERSION values",
    )
    ap.add_argument("--mode", default="clinical_speech")
    args = ap.parse_args()

    texts = _load_ru_samples(args.dataset)
    if not texts:
        print("ERROR: no sample lines", file=sys.stderr)
        return 2

    versions = [v.strip() for v in str(args.versions).split(",") if v.strip()]
    report: dict[str, Any] = {
        "run": args.run_label,
        "dataset": str(args.dataset.relative_to(REPO)) if args.dataset.is_relative_to(REPO) else str(args.dataset),
        "calibration_mode": args.mode,
        "notes": "Compare calibration versions; v052_5 = dict_c language metadata retag only (vs v052_4).",
    }
    key_alias = {
        "v0_6_0_clr_v052_2": "v052_2",
        "v0_6_0_clr_v052_3": "v052_3",
        "v0_6_0_clr_v052_4": "v052_4",
        "v0_6_0_clr_v052_5": "v052_5",
    }
    for v in versions:
        report[key_alias.get(v, v)] = evaluate_version(v, texts, mode=args.mode)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
