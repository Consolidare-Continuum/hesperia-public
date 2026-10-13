#!/usr/bin/env python3
# HESPERIA — RAD. Standalone: session topology JSON → triz_activation artifact bundle (Tasks 1–9).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build concept_coactivation_graph + contradiction chain from session_topology JSON."
    )
    ap.add_argument(
        "--topology-json",
        type=Path,
        required=True,
        help="JSON file containing { 'session_topology': { 'segments': [...] } } or full 09_session_topology session object",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory to write artifacts as flat 12_<session>_<name>.json (same layout as run_tfp_file_pipeline --with-topology)",
    )
    ap.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Session slug for 12_<session>_ prefix; default: session_id from JSON or 'session'",
    )
    ap.add_argument(
        "--triz-complete-json",
        type=Path,
        default=None,
        help="Optional 08-style JSON with triz_complete for innovation cluster enrichment",
    )
    args = ap.parse_args()
    raw = json.loads(args.topology_json.read_text(encoding="utf-8"))
    st = raw.get("session_topology") or raw
    tc = None
    if args.triz_complete_json and args.triz_complete_json.is_file():
        tc = json.loads(args.triz_complete_json.read_text(encoding="utf-8"))

    from hesperia.extensions.triz.topology_activation_pipeline import (
        run_topology_triz_activation,
        triz_activation_bundle_filename,
    )

    sid = (args.session_id or "").strip() or None
    if not sid and isinstance(raw, dict):
        sid = raw.get("session_id")
    if not sid and isinstance(st, dict):
        sid = st.get("session_id")
    sid = (str(sid).strip() if sid else "") or "session"

    bundle = run_topology_triz_activation(st, triz_complete=tc)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for fn, data in bundle.items():
        flat = triz_activation_bundle_filename(sid, fn)
        (out / flat).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(bundle)} files under {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
