#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Step 1 — language layer: compare heuristic text language to dict_c.language metadata.

Prints JSON to stdout and one line to stderr with the written report path (unless --quiet).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.lexical.text_lang import heuristic_document_language, match_language


def _analyze_dict_c(path: Path) -> dict[str, Any]:
    field_lang = Counter()
    inferred = Counter()
    mismatch_rows = 0
    rows = 0
    examples: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        rows += 1
        lf = str(o.get("language") or "en").strip().lower()
        field_lang[lf] += 1
        nf = str(o.get("normalized_form") or "")
        inf = heuristic_document_language(nf)
        inferred[inf] += 1
        if inf == "ru" and lf == "en":
            mismatch_rows += 1
            if len(examples) < 8:
                examples.append(
                    {
                        "entry_id": str(o.get("entry_id", "")),
                        "normalized_form": nf[:120],
                        "language_field": lf,
                        "inferred_from_script": inf,
                    }
                )
    return {
        "dict_c_path": str(path),
        "rows": rows,
        "language_field_counts": dict(field_lang),
        "inferred_from_normalized_form_script": dict(inferred),
        "rows_ru_script_but_language_field_en": mismatch_rows,
        "sample_mismatches": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dict-version-dir",
        type=Path,
        default=REPO / "assets" / "calibration" / "dicts" / "v0_6_0_clr_v052_5",
    )
    ap.add_argument(
        "--text-file",
        type=Path,
        help="Optional sample text file (e.g. Russian corpus) for match_language vs dict_c dominant field.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "assets" / "artifacts" / "calibration" / "dict_c_language_layer_report.json",
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    dc = args.dict_version_dir / "dict_c.jsonl"
    if not dc.is_file():
        print(f"ERROR: missing {dc}", file=sys.stderr)
        return 2

    payload: dict[str, Any] = {
        "dict_c_analysis": _analyze_dict_c(dc),
    }

    if args.text_file and args.text_file.is_file():
        raw = args.text_file.read_text(encoding="utf-8")
        # strip markdown-ish comments
        body_lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("#")]
        sample = "\n".join(body_lines).strip()
        doc_lang = match_language(sample)
        fl = payload["dict_c_analysis"]["language_field_counts"]
        dominant_field = max(fl, key=lambda k: fl[k]) if fl else "en"
        payload["sample_text_file"] = str(args.text_file)
        payload["sample_text_heuristic_language"] = doc_lang
        payload["dict_c_language_field_dominant"] = dominant_field
        payload["text_vs_dict_c_field_mismatch"] = doc_lang != dominant_field

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote: {args.out}", file=sys.stderr)
    if not args.quiet:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
