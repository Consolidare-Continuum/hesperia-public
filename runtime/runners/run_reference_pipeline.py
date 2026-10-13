#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct execution_flow import.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Public entry point: structural measurement. Delegates to runtime.services.analysis_service only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.artifact_writer import write_public_json

    ap = argparse.ArgumentParser(description="Run structural measurement (canonical entry point).")
    ap.add_argument("--text", default="justice lie fairness truth good order harm freedom")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--document-id", default="reference")
    ap.add_argument("--assets-root", type=Path, default=None)
    ap.add_argument("--policy-mode", dest="policy_mode", default=None)
    args = ap.parse_args()

    summary_payload = run_structural_analysis(
        args.text,
        assets_root=args.assets_root or (ROOT / "assets" / "lexicon" / "curated"),
        policy_mode=args.policy_mode,
        stages="full",
    )
    if args.out:
        write_public_json(args.out, summary_payload)
        print("Output written to", args.out, file=sys.stderr)
    print(json.dumps(summary_payload, indent=2))


if __name__ == "__main__":
    main()
