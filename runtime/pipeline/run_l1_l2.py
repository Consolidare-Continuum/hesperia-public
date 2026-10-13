#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct layer import.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Deprecated alias: runs **full** canonical multiscale measurement (hex layer required). L1-only shortcuts removed."""
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

    ap = argparse.ArgumentParser(description="Run canonical multiscale analysis (legacy name: L1+L2).")
    ap.add_argument("--text", type=str, default="justice lie fairness truth good order harm freedom")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--write", type=Path, default=None)
    args = ap.parse_args()
    out_path = args.out or args.write

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    print("Note: L1_L2 entry now maps to full sealed multiscale path (hex unavoidable).", file=sys.stderr)
    out = run_structural_analysis(args.text, assets_root=assets, stages="full")
    if out_path:
        write_public_json(out_path, out)
        print("L1+L2 output written to", out_path, file=sys.stderr)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
