#!/usr/bin/env python3
# HESPERIA — Thin wrapper over measurement service. No direct orchestration.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Public entry point: canonical multiscale structural analysis. Delegates to runtime.services.analysis_service only.
Usage: python3 -m runtime.pipeline.run_l1_through_l9 [--out path.json] [--write-dossier path]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))


def run_pipeline_for_text(
    text: str,
    assets_root: Path | None = None,
    defaults: dict | None = None,
    profile_id: str | None = None,
    profile: dict | None = None,
    policy_mode: str | None = None,
    profile_path: Path | None = None,
) -> dict:
    """Thin wrapper: run canonical multiscale measurement and return projected summary. For e2e and callers."""
    _ = (defaults, profile_id, profile, profile_path)  # deprecated; rejected if passed to service
    from runtime.services.analysis_service import run_structural_analysis
    assets = assets_root or _HESPERIA / "assets" / "lexicon" / "curated"
    out = run_structural_analysis(
        text,
        assets_root=assets,
        policy_mode=policy_mode,
        stages="full",
    )
    # Preserve L1_through_L9 contract for e2e and callers
    out["run"] = "L1_through_L9"
    return out


def main() -> None:
    import argparse
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.artifact_writer import write_public_json
    from runtime.dossier import validate_dossier_schema, write_dossier_json
    from runtime.dossier.index_manager import update_dossier_index
    from runtime.provenance import build_run_manifest, get_engine_provenance

    ap = argparse.ArgumentParser(description="Run structural analysis (public entry point).")
    ap.add_argument("--text", default="justice lie fairness truth good order harm freedom")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Removed: canonical path is sealed multiscale only. If set, execution fails.",
    )
    ap.add_argument("--policy-mode", dest="policy_mode", default=None, choices=("STRUCTURE_ONLY", "STRUCTURE_PLUS_CONTEXT", "FULL_INTERPRETATION"))
    ap.add_argument("--write-dossier", type=Path, default=None, metavar="PATH")
    ap.add_argument("--validate-dossier", action="store_true")
    args = ap.parse_args()

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    out = run_structural_analysis(
        args.text,
        assets_root=assets,
        profile_path=args.profile,
        policy_mode=getattr(args, "policy_mode", None),
        stages="full",
    )
    L7 = out.get("L7", {})
    L9 = out.get("L9", {})

    if getattr(args, "validate_dossier", False):
        try:
            validate_dossier_schema(out)
            print("Dossier schema validation passed.", file=sys.stderr)
        except ValueError as e:
            print("Dossier schema validation failed:", e, file=sys.stderr)
            sys.exit(1)
    if getattr(args, "write_dossier", None):
        dossier_payload = dict(out)
        dossier_payload.setdefault("meta", {})
        dossier_payload["meta"].update(get_engine_provenance())
        dossier_payload["meta"]["run_manifest"] = build_run_manifest(args, {}, None, None, assets)
        write_dossier_json(dossier_payload, args.write_dossier)
        update_dossier_index(args.write_dossier)
        print("Dossier written to", args.write_dossier, file=sys.stderr)
    if args.out:
        write_public_json(args.out, out)
        print("Output written to", args.out, file=sys.stderr)
    print(json.dumps(out, indent=2))
    if L7 or L9:
        print(
            "--- reportable --- L7 DECISION_STATUS_CODE:", L7.get("DECISION_STATUS_CODE"),
            "OUTPUT_TRUST_TAG:", L7.get("OUTPUT_TRUST_TAG"),
            "L9 BRAND_WORD_TRUST:", L9.get("BRAND_WORD_TRUST"),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
