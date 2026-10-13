#!/usr/bin/env python3
# HESPERIA — FPF-PRE07-06 agent-rolling harness (ops + dig, headless, no UI).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Run gold HAND loops: hesperia_ops → inquire/interpret ground_truth; hesperia_inspect → GapReport.

Usage (from Hesperia repo root, venv active)::

    python tools/fpf_hand_roll_harness.py
    python tools/fpf_hand_roll_harness.py --text "synthetic includes with something"

Exit 0 only when both loops assert green.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _ops_loop(text: str) -> dict[str, Any]:
    from sphere.fpf_inspect.map_hesperia_ops import ops_map_step
    from sphere.router.tool_inquiry import build_tool_inquiry_packet

    step1 = ops_map_step(current_state="start", current_evidence="", task="harness ops")
    inquire = build_tool_inquiry_packet(text)
    gt = inquire.get("ground_truth") or {}
    for key in ("logical", "weight", "source_activation"):
        if key not in gt:
            raise AssertionError(f"ops loop missing ground_truth.{key}")
    evidence = "runtime_ok inquire_done ground_truth_ok map_obeyed"
    step2 = ops_map_step(
        current_state="grounded",
        current_evidence=evidence,
        task="harness ops re-step",
    )
    return {
        "face": "hesperia_ops",
        "step1_kind": step1.get("kind"),
        "step2_kind": step2.get("kind"),
        "ground_truth_keys": sorted(gt.keys()),
        "router_fingerprint": (inquire.get("router_envelope") or {}).get("router_fingerprint"),
    }


def _dig_loop(text: str) -> dict[str, Any]:
    from sphere.fpf_inspect.climb import gap_detect, inspect_climb
    from sphere.fpf_inspect.map_hesperia_inspect import map_step
    from sphere.router.tool_inquiry import build_tool_inquiry_packet

    step1 = map_step(current_state="l0_hash", current_evidence="", task="harness dig")
    inquire = build_tool_inquiry_packet(text)
    engine = (inquire.get("router_envelope") or {}).get("engine_trace") or {}
    dig_input = dict(engine)
    dig_input.setdefault("router_envelope", inquire.get("router_envelope") or {})
    dig_input.setdefault("ground_truth", inquire.get("ground_truth") or {})
    climb = inspect_climb(dig_input, stop_on_first_gap=False)
    report = climb["gap_report"]
    report2 = gap_detect(dig_input)
    if json.dumps(report, sort_keys=True, default=str) != json.dumps(report2, sort_keys=True, default=str):
        raise AssertionError("dig loop GapReport not deterministic")
    step2 = map_step(
        current_state="gap_report",
        current_evidence="gap_report_done",
        task="harness dig re-step",
    )
    return {
        "face": "hesperia_inspect",
        "step1_kind": step1.get("kind"),
        "step2_kind": step2.get("kind"),
        "gap_schema": report.get("schema"),
        "slice_count": len(climb.get("slices") or []),
        "gap_count": len(report.get("gaps") or []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FPF HAND ops+dig harness")
    parser.add_argument(
        "--text",
        default="FPF-PRE07 synthetic harness text that includes with overlapping structure.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args(argv)

    ops = _ops_loop(args.text)
    dig = _dig_loop(args.text)
    out = {"ok": True, "ops": ops, "dig": dig}
    if args.json:
        sys.stdout.write(json.dumps(out, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(
            f"OK ops keys={ops['ground_truth_keys']} dig slices={dig['slice_count']} gaps={dig['gap_count']}\n"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — harness reports failure as exit 1
        sys.stderr.write(f"FAIL: {exc}\n")
        raise SystemExit(1) from exc
