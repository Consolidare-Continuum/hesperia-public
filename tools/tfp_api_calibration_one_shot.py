#!/usr/bin/env python3
# HESPERIA — RAD. One POST /analyze (shipping API) + TFP calibration sidecar (not in public JSON).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Run **one** product-path ``POST /analyze`` (same handler as ``runtime.shipping.api_main``) and write:

- ``public_analyze_response.json`` — API JSON (projected product schema).
- ``tfp_signal_calibration.json`` — same structure as ``00_manifest.json`` → ``tfp_signal_calibration``
  (topology/Dict-A knobs used by the TFP bundle; **not** returned by the public analyze endpoint).

Usage::

  PYTHONPATH=. python3 tools/tfp_api_calibration_one_shot.py \\
    -i tests/fixtures/clinical_tfp/tfp_ru_session_sample.md \\
    -o outputs/tfp_api_calibration_one_shot

For a live HTTP server instead of in-process TestClient, use curl::

  curl -sS -X POST http://127.0.0.1:PORT/analyze -H 'Content-Type: application/json' \\
    -d @- <<< '{"text":"..."}' > public_analyze_response.json
  # then copy tfp_signal_calibration.json from a TFP bundle or run this tool without --http-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _build_tfp_signal_calibration() -> dict[str, Any]:
    from hesperia.ontology.dictA.loader import CONFIDENCE_TYPE_MULTIPLIER
    from hesperia.engine.tfp_signal_calibration import load_tfp_runtime_bundle
    from research.clinical_tfp.session_topology import AREA_CURVE_MAP, CURVE_CALIBRATION_REFERENCE, DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS

    tfp_runtime = load_tfp_runtime_bundle()
    tfp_calibration = dict(tfp_runtime["calibration"])
    tfp_inhibition = dict(tfp_runtime["inhibition_matrix"])

    return {
        "run": "tfp_api_calibration_one_shot",
        "config_version": str(tfp_calibration.get("version") or "unknown"),
        "invariant_path_id": str(tfp_calibration.get("invariant_path_id") or "unknown"),
        "session_topology_run_params": dict(DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS),
        "loaded_config": tfp_calibration,
        "area_curve_map": dict(AREA_CURVE_MAP),
        "curve_calibration_reference": dict(CURVE_CALIBRATION_REFERENCE),
        "dict_a_confidence_multiplier": dict(CONFIDENCE_TYPE_MULTIPLIER),
        "inhibition_matrix": {
            "version": tfp_inhibition.get("version"),
            "date": tfp_inhibition.get("date"),
            "area_ids": tfp_inhibition.get("area_ids"),
            "intended_range": tfp_inhibition.get("intended_range"),
        },
        "note": (
            "Aligned with 00_manifest.json → tfp_signal_calibration. "
            "Public POST /analyze does not include these keys; use this sidecar next to API output."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Transcript or text file (UTF-8)",
    )
    ap.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: outputs/tfp_api_calibration_one_shot)",
    )
    ap.add_argument(
        "--calibration-only",
        action="store_true",
        help="Only write tfp_signal_calibration.json (no API call)",
    )
    args = ap.parse_args()

    inp = args.input.resolve()
    if not inp.is_file():
        print(f"ERROR: not a file: {inp}", file=sys.stderr)
        return 2

    out_dir = args.out_dir
    if out_dir is None:
        out_dir = REPO / "outputs" / "tfp_api_calibration_one_shot"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cal = _build_tfp_signal_calibration()
    cal_path = out_dir / "tfp_signal_calibration.json"
    cal_path.write_text(json.dumps(cal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.calibration_only:
        print(str(cal_path), file=sys.stderr)
        print(str(out_dir))
        return 0

    os.environ.setdefault("HESPERIA_REQUIRE_SYSTEM_SEAL", "0")

    text = inp.read_text(encoding="utf-8").strip()
    max_chars = int(os.environ.get("HESPERIA_MAX_INPUT_CHARS", "10000"))
    if len(text) > max_chars:
        text = text[:max_chars]

    try:
        from starlette.testclient import TestClient
    except ImportError:
        print("ERROR: starlette required (TestClient). pip install starlette", file=sys.stderr)
        return 2

    from runtime.shipping.api_main import create_app

    app = create_app()
    client = TestClient(app)
    r = client.post("/analyze", json={"text": text})
    if r.status_code != 200:
        print(r.text, file=sys.stderr)
        return 1

    pub_path = out_dir / "public_analyze_response.json"
    pub_path.write_text(json.dumps(r.json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = (
        "public_analyze_response.json — one POST /analyze (shipping API, in-process TestClient).\n"
        "tfp_signal_calibration.json — TFP/Dict-A knobs (same as 00_manifest.tfp_signal_calibration); "
        "not part of the public analyze payload.\n"
        "See docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md\n"
    )
    (out_dir / "README.txt").write_text(readme, encoding="utf-8")

    print(f"wrote {pub_path}", file=sys.stderr)
    print(f"wrote {cal_path}", file=sys.stderr)
    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
