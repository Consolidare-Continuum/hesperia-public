#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct layer import.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Public entry point: structural analysis, write one JSON. Delegates to runtime.services.analysis_service only.
Usage: python3 -m runtime.pipeline.run_sphere_math_values [--out path.json] [--profile path] [--text "input"]
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))


def main() -> None:
    import argparse
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.artifact_writer import get_runtime_mode, write_public_json

    ap = argparse.ArgumentParser(description="Run structural analysis, write one JSON.")
    ap.add_argument("--out", type=Path, default=_HESPERIA / "sphere_math_values.json")
    ap.add_argument("--profile", type=Path, default=None)
    ap.add_argument("--text", default="justice lie fairness truth good order harm freedom")
    args = ap.parse_args()

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    out = run_structural_analysis(
        args.text,
        assets_root=assets,
        profile_path=args.profile,
        stages="full",
    )
    write_public_json(args.out, out)
    if sys.stdout.isatty():
        print(Path(args.out).resolve(), file=sys.stderr)


if __name__ == "__main__":
    main()
