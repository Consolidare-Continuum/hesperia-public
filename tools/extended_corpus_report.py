#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""EXTENDED CORPUS REPORT: aggregate DLCR metrics over chunked Russian text (no dict changes)."""

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


def _chunk_by_words(lines: list[str], chunk_words: int) -> list[str]:
    """Join lines and split into chunks of approximately ``chunk_words`` words."""
    flat: list[str] = []
    buf: list[str] = []
    n = 0
    for line in lines:
        for w in line.split():
            buf.append(w)
            n += 1
            if n >= chunk_words:
                flat.append(" ".join(buf))
                buf = []
                n = 0
    if buf:
        flat.append(" ".join(buf))
    return flat


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
        "token_contribution_ratio": round(1.0 - phrase_hit, 6) if n_res else 1.0,
        "concept_activation_from_c_ratio": phrase_hit,
        "blocked_token_ratio_est": round(
            sum(blocked_ratios) / max(1, len(blocked_ratios)), 6
        ),
        "used_concepts_count": len(agg_cw),
        "n_chunks": len(texts),
        "n_span_resolutions": n_res,
        "n_c_span_resolutions": n_c_res,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Extended corpus REPORT (v052_4, measurement only).")
    ap.add_argument(
        "--corpus",
        type=Path,
        help="Text file: one segment per line (or full text).",
    )
    ap.add_argument(
        "--chunk-words",
        type=int,
        default=600,
        help="Join lines and split into chunks of this many words per pipeline run.",
    )
    ap.add_argument("--version", default="v0_6_0_clr_v052_4")
    ap.add_argument("--mode", default="clinical_speech")
    ap.add_argument("--out", type=Path, default=REPO / "outputs" / "reports" / "extended_corpus_report_v052_4.json")
    args = ap.parse_args()

    if not args.corpus or not args.corpus.is_file():
        print("ERROR: --corpus path required and must exist", file=sys.stderr)
        return 2

    raw_lines = [
        ln.strip()
        for ln in args.corpus.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    total_words = sum(len(ln.split()) for ln in raw_lines)
    chunks = _chunk_by_words(raw_lines, args.chunk_words)
    if not chunks:
        print("ERROR: empty corpus", file=sys.stderr)
        return 2

    report = {
        "run": "extended_corpus_report_v1",
        "calibration_version": args.version,
        "corpus_path": str(args.corpus),
        "corpus_line_count": len(raw_lines),
        "corpus_word_count": total_words,
        "chunk_words": args.chunk_words,
        "mode": args.mode,
        args.version.replace("v0_6_0_clr_", ""): evaluate_version(args.version, chunks, mode=args.mode),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
