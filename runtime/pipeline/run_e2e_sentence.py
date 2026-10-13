#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
E2E: run one sentence through analyze (6-key SUMMARY + attribution + dict_b + R1–R4).
Output JSON contains all computed math: SUMMARY and DIAGNOSTICS (attribution, dict_b, r1_r4 units + book_profile).
Usage: python3 -m runtime.pipeline.run_e2e_sentence [--text "sentence"] [--out path.json] [--no-r1-r4] [--truncate-vector]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parents[1]) not in sys.path:
    sys.path.insert(0, str(_HERE.parents[1]))


def _round_floats(obj, ndigits=6):
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x, ndigits) for x in obj]
    return obj


def _format_txt_report(out: dict) -> str:
    """Build a .txt report: header, per-phrase (R1), per-paragraph (R2), scale/smooth, then full JSON."""
    lines = []
    diagnostics = out.get("diagnostics") or out.get("extended") or {}
    r1_r4 = diagnostics.get("r1_r4") or {}
    units = r1_r4.get("units") or []
    book_profile = r1_r4.get("book_profile") or {}

    lines.append("=" * 60)
    lines.append("E2E RUN OUTPUT — full math (per phrase, per paragraph, scale & smooth)")
    lines.append("=" * 60)
    lines.append("")
    inp = out.get("raw_text") or out.get("input") or {}
    lines.append("INPUT: length={}  preview={}".format(inp.get("length", 0), (inp.get("text_preview") or "")[:80]))
    lines.append("")
    res = out.get("summary") or out.get("result") or {}
    lines.append("RESULT (6-key): dominant_area={} dominant_family={} governance={} loopability={} tension_energy={} obstacle_score={}".format(
        res.get("dominant_area"), res.get("dominant_family"), res.get("governance"),
        res.get("loopability"), res.get("tension_energy"), res.get("obstacle_score")))
    lines.append("")

    r1_units = [u for u in units if (u.get("level") or "") == "R1"]
    lines.append("--- PER PHRASE (R1) ---")
    for u in r1_units:
        lines.append("  {}  token_count={}  band={}  decision_code={}".format(
            u.get("unit_id", ""), u.get("token_count", 0),
            (u.get("flags") or {}).get("band", ""), (u.get("flags") or {}).get("decision_code", "")))
        si = u.get("SI_metrics") or {}
        lines.append("    SI_metrics: coverage={} dominance={} entropy={} leakage={} stability={} trust_tier={}".format(
            si.get("coverage"), si.get("dominance"), si.get("entropy"),
            si.get("leakage"), si.get("stability"), si.get("trust_tier")))
    lines.append("")

    r2_units = [u for u in units if (u.get("level") or "") == "R2"]
    lines.append("--- PER PARAGRAPH (R2) ---")
    for u in r2_units:
        lines.append("  {}  token_count={}  band={}  decision_code={}".format(
            u.get("unit_id", ""), u.get("token_count", 0),
            (u.get("flags") or {}).get("band", ""), (u.get("flags") or {}).get("decision_code", "")))
        si = u.get("SI_metrics") or {}
        lines.append("    SI_metrics: coverage={} dominance={} entropy={} leakage={} stability={} trust_tier={}".format(
            si.get("coverage"), si.get("dominance"), si.get("entropy"),
            si.get("leakage"), si.get("stability"), si.get("trust_tier")))
    lines.append("")

    lines.append("--- SCALE & SMOOTH (level_averages, scale_deltas) ---")
    la = book_profile.get("level_averages") or {}
    for level in ("R1", "R2", "R3", "R4"):
        if level not in la:
            continue
        L = la[level]
        lines.append("  {}: token_count_total={}  SCI={}".format(
            level, L.get("token_count_total", 0), L.get("SCI", 0)))
        sm = (L.get("SI_means") or {})
        lines.append("    SI_means: coverage={} dominance={} entropy={} leakage={} stability={}".format(
            sm.get("coverage"), sm.get("dominance"), sm.get("entropy"), sm.get("leakage"), sm.get("stability")))
    sd = book_profile.get("scale_deltas") or {}
    for band in ("R1_to_R2", "R2_to_R3", "R3_to_R4"):
        if band not in sd:
            continue
        d = sd[band]
        obs = d.get("delta_observed") or {}
        exp = d.get("delta_expected") or {}
        dev = d.get("delta_deviation") or {}
        lines.append("  {}: delta_observed(coverage={}, dominance={})  delta_expected(dominance={})  delta_deviation(coverage={})".format(
            band, obs.get("coverage"), obs.get("dominance"), exp.get("dominance"), dev.get("coverage")))
    lines.append("")
    lines.append("structural_signature.stable_families: {}".format(
        (book_profile.get("structural_signature") or {}).get("stable_families", [])))
    lines.append("")
    lines.append("=" * 60)
    lines.append("FULL JSON")
    lines.append("=" * 60)
    lines.append(json.dumps(out, indent=2))
    return "\n".join(lines)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="E2E: one sentence -> full output (SUMMARY + DIAGNOSTICS + R1-R4 units & book_profile)."
    )
    ap.add_argument(
        "--text",
        default="Justice and fairness support social order. Harm and conflict reduce trust.",
        help="Input sentence(s)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_HERE.parents[1] / "assets" / "artifacts" / "e2e" / "run_output_e2e_sentence.json",
        help="Output JSON path",
    )
    ap.add_argument(
        "--no-r1-r4",
        action="store_true",
        help="Do not run R1-R4 execution flow (diagnostics.r1_r4 will be absent)",
    )
    ap.add_argument(
        "--truncate-vector",
        action="store_true",
        help="Write family_vector as length only in diagnostics (keeps file small)",
    )
    ap.add_argument(
        "--no-round",
        action="store_true",
        help="Do not round floats in output",
    )
    args = ap.parse_args()

    text = (args.text or "").strip()
    if not text:
        print("Error: empty --text", file=sys.stderr)
        return 1

    try:
        from runtime.pipeline.analyze import analyze
    except ImportError:
        print("Error: cannot import runtime.pipeline.analyze", file=sys.stderr)
        return 1

    try:
        minimal, extended = analyze(
            text,
            r1_r4=not args.no_r1_r4,
            r1_r4_book_id="e2e",
            r1_r4_levels=["R1", "R2", "R3", "R4"],
        )
    except Exception as e:
        print(f"Error: analyze failed: {e}", file=sys.stderr)
        return 1

    out = {
        "raw_text": {
            "text_preview": text[:200] + ("..." if len(text) > 200 else ""),
            "length": len(text),
        },
        "summary": minimal,
        "diagnostics": dict(extended),
        # Compatibility mirror.
        "extended": dict(extended),
    }

    if args.truncate_vector and isinstance(out["diagnostics"].get("family_vector"), list):
        out["diagnostics"]["family_vector"] = {"length": len(out["diagnostics"]["family_vector"]), "_truncated": True}
        out["extended"]["family_vector"] = out["diagnostics"]["family_vector"]
    if args.truncate_vector and isinstance(out["diagnostics"].get("family_vector_pre_sharpen"), list):
        out["diagnostics"]["family_vector_pre_sharpen"] = {
            "length": len(out["diagnostics"]["family_vector_pre_sharpen"]),
            "_truncated": True,
        }
        out["extended"]["family_vector_pre_sharpen"] = out["diagnostics"]["family_vector_pre_sharpen"]

    if not args.no_round:
        out = _round_floats(out)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".txt":
        out_path.write_text(_format_txt_report(out), encoding="utf-8")
    else:
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    if sys.stdout.isatty():
        print(out_path.resolve(), file=sys.stderr)
    else:
        print(out_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
