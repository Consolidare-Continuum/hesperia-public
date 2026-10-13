#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Optional: assemble a long text from tfp_rel + sealed dict surfaces (stress / coverage only).

For **phrase metric validation** on natural Russian, use instead:
``python3 tools/fetch_extended_ru_natural_corpus.py``
and ``tests/fixtures/tfp_calibration/extended_ru_natural_corpus_v1.txt``.

Bulk ``dict_c`` lines are **not** natural language and will **invalidate** phrase_hit_ratio.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _strip_tfp_rel_line(s: str) -> str:
    s = s.strip()
    if not s or s.startswith("#"):
        return ""
    m = re.match(r"^\d{4}\s+(.*)$", s)
    return m.group(1).strip() if m else s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--dict-version-dir",
        type=Path,
        default=REPO / "assets" / "calibration" / "dicts" / "v0_6_0_clr_v052_4",
    )
    ap.add_argument("--min-words", type=int, default=5000)
    ap.add_argument("--max-words", type=int, default=18000)
    ap.add_argument(
        "--include-dict-c-surface",
        action="store_true",
        help="Append dict A/C normalized surfaces until word budget (not valid for phrase dominance metrics).",
    )
    args = ap.parse_args()

    if not args.include_dict_c_surface:
        print(
            "ERROR: Natural extended validation uses Wikipedia-backed corpus. Run:\n"
            "  python3 tools/fetch_extended_ru_natural_corpus.py\n"
            "Only use --include-dict-c-surface for stress/coverage experiments (phrase metrics misleading).",
            file=sys.stderr,
        )
        return 2

    print(
        "WARNING: dict_c/dict_a surface bulk — phrase_hit_ratio will be artifactually high; not for Ethan gates.",
        file=sys.stderr,
    )

    lines: list[str] = []
    wc = 0
    ddir = args.dict_version_dir.resolve()

    p = REPO / "tests" / "fixtures" / "tfp_rel_real_corpus.txt"
    if p.is_file():
        for raw in p.read_text(encoding="utf-8").splitlines():
            t = _strip_tfp_rel_line(raw)
            if t:
                lines.append(t)
                wc += len(t.split())

    dc = ddir / "dict_c.jsonl"
    if dc.is_file():
        for row in dc.read_text(encoding="utf-8").splitlines():
            if not row.strip():
                continue
            o = json.loads(row)
            nf = str(o.get("normalized_form") or "").strip()
            if not nf:
                continue
            lines.append(nf)
            wc += len(nf.split())
            if wc >= args.max_words:
                break

    da = ddir / "dict_a.jsonl"
    if da.is_file() and wc < args.min_words:
        n = 0
        for row in da.read_text(encoding="utf-8").splitlines():
            if not row.strip():
                continue
            o = json.loads(row)
            s = str(o.get("normalized_form") or o.get("surface_form") or "").strip()
            if not s:
                continue
            n += 1
            if n % 2 != 0:
                continue
            lines.append(s)
            wc += len(s.split())
            if wc >= args.min_words:
                break

    text = "\n".join(lines)
    words = len(text.split())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "lines": len(lines), "word_count": words}, indent=2))
    if words < args.min_words:
        print("ERROR: word_count < min-words", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
