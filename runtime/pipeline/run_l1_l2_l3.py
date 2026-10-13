#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct layer import.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Deprecated alias: runs **full** canonical multiscale measurement. L1–L3-only shortcuts removed."""
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
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.artifact_writer import write_public_json

    ap = argparse.ArgumentParser(description="Run canonical multiscale analysis (legacy name: L1+L2+L3).")
    ap.add_argument("--text", type=str, default="justice lie fairness truth good order harm freedom")
    ap.add_argument("--text-s", type=str, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    text_s = args.text_s or args.text

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    print("Note: L1_L2_L3 entry now maps to full sealed multiscale path (hex unavoidable).", file=sys.stderr)
    out = run_structural_analysis(args.text, assets_root=assets, stages="full")
    if args.out:
        write_public_json(args.out, out)
        print("L1+L2+L3 output written to", args.out, file=sys.stderr)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
