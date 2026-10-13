#!/usr/bin/env python3
"""
Fuel-chamber capacity measurement.

Hesperia's semantic fuel (tokens) is burned into a dominant family/area by
core.attribution.attribution_shared.run_attribution_pipeline — the sole live
core attribution pipeline (core has no relation to any extension/module; see
docs/foundations/attribution_layer.md). The former "v06" pipeline
(core.attribution.attribution) has been retired — see
core/attribution/_deprecated/README.md — it loaded a synthetic-placeholder
dictionary with zero real vocabulary and is no longer measured here.

The frozen B0 token->family map (lexicon/frozen/B0_TOKEN_TO_FAMILY_*.json) is
the engine's own ground-truth fuel catalog: 3198 tokens, each labeled with the
family it is supposed to land in. This tool runs every one of those tokens
through the real pipeline and checks whether the engine reproduces its own
label. Pass rate per family/area is the family's/area's logical capacity: how
much of its labeled fuel the chamber currently combusts correctly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.attribution.attribution_shared import (
    aggregate_dominant,
    attribute,
    load_dict_a_surface_map_v033,
    load_dict_a_v033,
    load_dict_b_v033,
    normalize,
    tokenize,
)
from core.topology.invariant_catalog import AREAS, FAMILIES_PER_AREA, TOTAL_FAMILIES

GROUND_TRUTH_PATH = REPO / "assets" / "lexicon" / "frozen" / "B0_TOKEN_TO_FAMILY_v0_4_1_4_from_A_v0_4_1_3.json"
REPORT_JSON = REPO / "outputs" / "reports" / "fuel_chamber_capacity.json"
REPORT_MD = REPO / "outputs" / "reports" / "FUEL-CHAMBER-CAPACITY-LEDGER.md"

CANONICAL_AREA_NAMES = [
    "GOOD", "CARE", "ORDER", "CONTROL", "INDIFFERENCE", "HARM",
    "DESTRUCTION", "CHAOS", "FREEDOM", "TRUTH", "CREATION", "DECEIT",
]


def load_ground_truth() -> dict[str, int]:
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return {str(k).strip().lower(): int(v) for k, v in data.items()}


def measure_capacity() -> dict[str, Any]:
    """
    Run every ground-truth token through the real attribution steps
    (normalize -> tokenize -> attribute -> aggregate_dominant, same steps
    run_attribution_pipeline chains) and tally pass/fail per family/area.

    Loads Dict A / Dict B / surface map once and reuses them across all 3198
    tokens (run_attribution_pipeline reloads those JSON assets from disk on
    every call, which is too slow to run repeatedly in a test suite).
    Exact-match only: an unmatched token fails cleanly (semantic_vacuum).
    """
    ground_truth = load_ground_truth()
    dict_a = load_dict_a_v033()
    dict_b = load_dict_b_v033()
    surface_map = load_dict_a_surface_map_v033() or None

    family_totals = [0] * TOTAL_FAMILIES
    family_pass = [0] * TOTAL_FAMILIES
    failures: list[dict[str, Any]] = []

    for token, expected_family in ground_truth.items():
        family_totals[expected_family] += 1
        normalized = normalize(token)
        tokens = tokenize(normalized)
        matched, _ = attribute(tokens, dict_a, dict_b, surface_map=surface_map) if tokens else ([], {})
        if not matched:
            failures.append({
                "token": token,
                "expected_family": expected_family,
                "expected_area": expected_family // FAMILIES_PER_AREA,
                "actual_family": None,
                "actual_area": None,
                "reason": "semantic_vacuum: no tokens matched any dictionary",
            })
            continue
        dominant_family, dominant_area, *_ = aggregate_dominant(matched)
        if dominant_family == expected_family:
            family_pass[expected_family] += 1
        else:
            failures.append({
                "token": token,
                "expected_family": expected_family,
                "expected_area": expected_family // FAMILIES_PER_AREA,
                "actual_family": dominant_family,
                "actual_area": dominant_area,
                "reason": "mismatch",
            })

    families: list[dict[str, Any]] = []
    for fid in range(TOTAL_FAMILIES):
        total = family_totals[fid]
        passed = family_pass[fid]
        families.append({
            "family_id": fid,
            "area_id": fid // FAMILIES_PER_AREA,
            "fuel_tokens": total,
            "pass": passed,
            "capacity": (passed / total) if total else None,
        })

    areas: list[dict[str, Any]] = []
    for aid in range(AREAS):
        fams = [f for f in families if f["area_id"] == aid]
        total = sum(f["fuel_tokens"] for f in fams)
        passed = sum(f["pass"] for f in fams)
        families_with_fuel = sum(1 for f in fams if f["fuel_tokens"] > 0)
        areas.append({
            "area_id": aid,
            "area_name": CANONICAL_AREA_NAMES[aid] if aid < len(CANONICAL_AREA_NAMES) else f"area_{aid}",
            "fuel_tokens": total,
            "pass": passed,
            "capacity": (passed / total) if total else None,
            "families_with_fuel": families_with_fuel,
            "families_total": FAMILIES_PER_AREA,
        })

    overall_total = sum(family_totals)
    overall_pass = sum(family_pass)
    dead_families = [f["family_id"] for f in families if f["fuel_tokens"] > 0 and f["capacity"] == 0.0]
    untested_families = [f["family_id"] for f in families if f["fuel_tokens"] == 0]

    return {
        "overall": {
            "fuel_tokens": overall_total,
            "pass": overall_pass,
            "capacity": (overall_pass / overall_total) if overall_total else 0.0,
        },
        "areas": areas,
        "families": families,
        "dead_families": dead_families,
        "untested_families": untested_families,
        "failures": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# Fuel Chamber Capacity Ledger",
        "",
        f"Overall logical capacity: **{overall['capacity']:.1%}** "
        f"({overall['pass']}/{overall['fuel_tokens']} labeled tokens correctly attributed to their family)",
        "",
        f"Dead families (fuel present, 0% capacity): {len(report['dead_families'])}",
        f"Untested families (no ground-truth fuel in catalog): {len(report['untested_families'])}",
        "",
        "## By area",
        "",
        "| area | name | fuel tokens | pass | capacity | families w/ fuel |",
        "|---|---|---|---|---|---|",
    ]
    for area in report["areas"]:
        cap = f"{area['capacity']:.1%}" if area["capacity"] is not None else "n/a"
        lines.append(
            f"| {area['area_id']} | {area['area_name']} | {area['fuel_tokens']} | "
            f"{area['pass']} | {cap} | {area['families_with_fuel']}/{area['families_total']} |"
        )
    lines += ["", "## Dead families (fuel present, 0% capacity)", ""]
    lines.append(", ".join(str(f) for f in report["dead_families"]) or "(none)")
    lines += ["", "## Untested families (no ground-truth fuel)", ""]
    lines.append(", ".join(str(f) for f in report["untested_families"]) or "(none)")
    return "\n".join(lines) + "\n"


def main() -> int:
    report = measure_capacity()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    overall = report["overall"]
    print(f"overall capacity: {overall['capacity']:.1%} ({overall['pass']}/{overall['fuel_tokens']})")
    print(f"dead families: {len(report['dead_families'])}")
    print(f"untested families: {len(report['untested_families'])}")
    print(f"wrote {REPORT_JSON}")
    print(f"wrote {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
