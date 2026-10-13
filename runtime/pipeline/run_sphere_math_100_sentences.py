#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct layer import.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Public entry point: structural analysis on multiple texts; write one JSON. Delegates to runtime.services.analysis_service only.
Usage: python3 -m runtime.pipeline.run_sphere_math_100_sentences [--out path.json] [--sentences path.json] [--limit N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))


def main() -> None:
    import argparse
    from runtime.services.analysis_service import run_structural_analysis_batch
    from runtime.artifact_writer import write_public_json

    ap = argparse.ArgumentParser(description="Run structural analysis on calibration sentences.")
    ap.add_argument("--out", type=Path, default=_HESPERIA / "sphere_math_100_sentences.txt")
    ap.add_argument("--sentences", type=Path, default=_HESPERIA / "tools" / "calibration" / "data" / "calibration_100_sentences.json")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not args.sentences.exists():
        print(f"Sentences file not found: {args.sentences}", file=sys.stderr)
        sys.exit(1)
    with open(args.sentences, encoding="utf-8") as f:
        sentences = json.load(f)
    if args.limit is not None:
        sentences = sentences[: args.limit]
    texts = [s.get("text", "") for s in sentences]
    results = run_structural_analysis_batch(
        texts,
        assets_root=_HESPERIA / "assets" / "lexicon" / "curated",
        attach_version=False,
    )
    out_list = []
    for i, (s, res) in enumerate(zip(sentences, results)):
        out_list.append({
            "id": s.get("id", i + 1),
            "domain": s.get("domain", ""),
            "text_preview": (s.get("text", ""))[:80],
            **res,
        })
    write_public_json(args.out, out_list)
    if sys.stdout.isatty():
        print(Path(args.out).resolve(), file=sys.stderr)


if __name__ == "__main__":
    main()
