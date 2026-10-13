#!/usr/bin/env python3
# HESPERIA — TFP parametric sweep driver.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Run the same input through gena_tfp_bundle_run.py once per named env/flag combo, and produce
a side-by-side yield comparison — the batch counterpart to a single `docs/recipes/params_combo/`
recipe, not a replacement for one. Chiron's own standing calibration toolchain (spec §8b): this
orchestrates existing pieces (gena_tfp_bundle_run.py, calibration_release_gate.py) rather than
inventing a new evaluation method.

Sweep spec JSON shape:
    {
      "sweep_id": "dlcr_dict_pin",
      "input": "tests/fixtures/tfp/input.txt",        # optional, --input overrides
      "gate_profile": "internal_review",               # optional, --gate-profile overrides
      "combos": [
        {"name": "baseline_unset", "env": {}, "clear": ["HESPERIA_DLCR_STRUCTURAL", "HESPERIA_CALIB_DICT_VERSION"]},
        {"name": "dlcr_on_dict_pinned", "env": {"HESPERIA_DLCR_STRUCTURAL": "1", "HESPERIA_CALIB_DICT_VERSION": "v0_6_0_clr_v052_5"}, "flags": []}
      ]
    }

Each combo runs in its own output subdirectory (full pipeline bundle preserved, nothing
overwritten) and the sweep report pulls: concept_weights count, lexical_hits_accepted/rejected,
dominant_area/dominant_family, tension/loopability/stability (all from 04_dlcr_full.json's first
session) plus the calibration_release_gate.py verdict (11_calibration_release_gate.json).

Usage:
    python3 tools/tfp_param_sweep.py --spec <spec.json> --out-dir outputs/tfp/sweeps/<sweep_id>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _run_combo(
    input_path: Path,
    out_dir: Path,
    combo: dict[str, Any],
    gate_profile: str,
) -> dict[str, Any]:
    name = combo["name"]
    combo_out = out_dir / name
    combo_out.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    for key in combo.get("clear") or []:
        env.pop(key, None)
    for key, val in (combo.get("env") or {}).items():
        env[str(key)] = str(val)

    cmd = [
        sys.executable,
        str(REPO / "tools" / "gena_tfp_bundle_run.py"),
        "-i",
        str(input_path),
        "-o",
        str(combo_out),
        "--gate-profile",
        gate_profile,
    ]
    cmd.extend(combo.get("flags") or [])

    proc = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True, check=False)

    row: dict[str, Any] = {
        "name": name,
        "env": combo.get("env") or {},
        "clear": combo.get("clear") or [],
        "flags": combo.get("flags") or [],
        "returncode": proc.returncode,
        "out_dir": str(combo_out),
    }

    dlcr_path = combo_out / "04_dlcr_full.json"
    if dlcr_path.is_file():
        try:
            dlcr = json.loads(dlcr_path.read_text(encoding="utf-8"))
            sess = (dlcr.get("sessions") or [{}])[0]
            row["concept_weights_count"] = len(sess.get("concept_weights") or {})
            row["lexical_hits_accepted"] = sess.get("lexical_hits_accepted")
            row["lexical_hits_rejected"] = sess.get("lexical_hits_rejected")
            row["dominant_area"] = sess.get("dominant_area")
            row["dominant_family"] = sess.get("dominant_family")
            row["tension"] = sess.get("tension")
            row["loopability"] = sess.get("loopability")
            row["stability"] = sess.get("stability")
        except (json.JSONDecodeError, IndexError, TypeError) as ex:  # noqa: BLE001
            row["dlcr_parse_error"] = str(ex)
    else:
        row["dlcr_parse_error"] = "04_dlcr_full.json not written (skip-dlcr? pipeline error?)"

    gate_path = combo_out / "11_calibration_release_gate.json"
    if gate_path.is_file():
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            row["gate_pass"] = gate.get("pass")
            row["gate_blocking_reason"] = gate.get("blocking_reason")
        except json.JSONDecodeError as ex:  # noqa: BLE001
            row["gate_parse_error"] = str(ex)
    else:
        row["gate_pass"] = None
        row["gate_blocking_reason"] = "11_calibration_release_gate.json not written"

    if proc.returncode not in (0,) and "dlcr_parse_error" not in row:
        row["pipeline_stderr_tail"] = "\n".join((proc.stderr or "").splitlines()[-10:])

    return row


def _render_markdown(sweep_id: str, goal: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# TFP parametric sweep — {sweep_id}",
        "",
        f"**Goal**: {goal}" if goal else "",
        "",
        "| Combo | concept_weights | lexical✓/✗ | dominant (area/family) | tension | stability | gate pass |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lex = f"{r.get('lexical_hits_accepted', '—')}/{r.get('lexical_hits_rejected', '—')}"
        dom = f"{r.get('dominant_area', '—')}/{r.get('dominant_family', '—')}"
        lines.append(
            f"| {r['name']} | {r.get('concept_weights_count', '—')} | {lex} | {dom} | "
            f"{r.get('tension', '—')} | {r.get('stability', '—')} | {r.get('gate_pass', '—')} |"
        )
    lines.append("")
    lines.append("Full per-combo bundles (all pipeline artifacts) under each combo's own subdirectory.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a named parametric sweep across gena_tfp_bundle_run.py combos.")
    ap.add_argument("--spec", type=Path, required=True, help="Sweep spec JSON (see module docstring)")
    ap.add_argument("--input", type=Path, default=None, help="Override spec's input file")
    ap.add_argument("--gate-profile", default=None, help="Override spec's gate_profile")
    ap.add_argument("--out-dir", type=Path, default=None, help="Default: outputs/tfp/sweeps/<sweep_id>")
    args = ap.parse_args()

    spec_path = args.spec.resolve()
    if not spec_path.is_file():
        print(f"ERROR: spec not found: {spec_path}", file=sys.stderr)
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    sweep_id = spec.get("sweep_id") or spec_path.stem
    goal = spec.get("goal") or ""
    combos = spec.get("combos") or []
    if not combos:
        print("ERROR: spec has no combos", file=sys.stderr)
        return 2

    input_path = (args.input or Path(spec.get("input", "tests/fixtures/tfp/input.txt"))).resolve()
    if not input_path.is_file():
        print(f"ERROR: input not a file: {input_path}", file=sys.stderr)
        return 2

    gate_profile = args.gate_profile or spec.get("gate_profile") or "internal_review"

    out_dir = (args.out_dir or REPO / "outputs" / "tfp" / "sweeps" / sweep_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [_run_combo(input_path, out_dir, combo, gate_profile) for combo in combos]

    report = {
        "run": "tfp_param_sweep",
        "sweep_id": sweep_id,
        "goal": goal,
        "input": str(input_path),
        "gate_profile": gate_profile,
        "combos": rows,
    }
    (out_dir / "sweep_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = _render_markdown(sweep_id, goal, rows)
    (out_dir / "SWEEP-REPORT.md").write_text(md, encoding="utf-8")

    print(md)
    print(f"tfp_param_sweep: wrote {out_dir / 'sweep_report.json'} and {out_dir / 'SWEEP-REPORT.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
