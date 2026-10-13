#!/usr/bin/env python3
# HESPERIA — Deterministic compiler for h_total_concepts.json (offline build).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Default inputs = mainline (dict_b_seed + semantic_dynamics/area_inhibition_matrix_main_v1.json).
# TFP dicts and tfp/area_inhibition_matrix_tfp.json are NOT touched unless you pass --use-tfp-inputs
# (operator-only; coordinate with Grace boundary on calibration).

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

V060 = REPO_ROOT / "assets" / "data" / "engine_dynamics_v060"

DEFAULT_DICT_B = V060 / "dict_b" / "dict_b_seed.jsonl"
DEFAULT_INHIBITION_MAIN = V060 / "semantic_dynamics" / "area_inhibition_matrix_main_v1.json"

# TFP paths — only used with --use-tfp-inputs
DICT_B_TFP = V060 / "dict_b" / "dict_b_tfp.jsonl"
INHIBITION_TFP = V060 / "tfp" / "area_inhibition_matrix_tfp.json"

DEFAULT_OUT = REPO_ROOT / "outputs" / "semantic_dynamics" / "h_total_concepts.json"
ASSET_PIN = V060 / "semantic_dynamics" / "h_total_concepts.json"

# Build constants (docs/semantic_dynamics_operator_spec.md)
DIAG_BASE = 0.45
DIAG_SPEC_BONUS = 0.10
DIAG_SPEC_RANK_CUTOFF = 8
DIAG_MIN = 0.35
DIAG_MAX = 0.75

COUP_SAME_FAMILY = 0.30
COUP_SAME_AREA_DIFF_FAMILY = 0.15
COUP_ANCHOR_SCALE = 0.20
COUP_MAX = 0.60

INHIB_MAX = 0.80
SPEC_FACTOR_MIN = 0.35
SPEC_FACTOR_MAX = 1.0
ROUND_DIGITS = 6


def _parse_hex_index(anchor: str | None) -> int:
    if not anchor or not isinstance(anchor, str):
        return 0
    s = anchor.strip()
    if s.upper().startswith("HX-"):
        try:
            return int(s.split("-", 1)[1], 10)
        except (ValueError, IndexError):
            return 0
    return 0


def _area_to_index(aid: str | None) -> int:
    if not aid or not isinstance(aid, str) or not aid.startswith("A"):
        return -1
    try:
        return int(aid[1:], 10) - 1
    except ValueError:
        return -1


def _load_dict_b(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _load_inhibition_matrix(path: Path) -> tuple[list[str], list[list[float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    area_ids = [str(x) for x in data["area_ids"]]
    matrix = data["matrix"]
    return area_ids, matrix


def _diagonal_value(spec_rank: int) -> float:
    r = int(spec_rank)
    v = DIAG_BASE
    if r <= DIAG_SPEC_RANK_CUTOFF:
        v += DIAG_SPEC_BONUS
    return max(DIAG_MIN, min(DIAG_MAX, v))


def _coupling(ci: dict[str, Any], cj: dict[str, Any]) -> float:
    fis = [str(x) for x in (ci.get("family_ids") or [])]
    fjs = [str(x) for x in (cj.get("family_ids") or [])]
    ais = [str(x) for x in (ci.get("area_ids") or [])]
    ajs = [str(x) for x in (cj.get("area_ids") or [])]
    fi = fis[0] if fis else ""
    fj = fjs[0] if fjs else ""
    ai = ais[0] if ais else ""
    aj = ajs[0] if ajs else ""

    c = 0.0
    if fi and fi == fj:
        c += COUP_SAME_FAMILY
    elif ai and ai == aj:
        c += COUP_SAME_AREA_DIFF_FAMILY

    hi = _parse_hex_index(ci.get("hex_anchor"))
    hj = _parse_hex_index(cj.get("hex_anchor"))
    d = abs(hi - hj)
    c += (1.0 / (1.0 + float(d))) * COUP_ANCHOR_SCALE

    return min(c, COUP_MAX)


def _specificity_factor(rank_i: int, rank_j: int) -> float:
    m = min(int(rank_i), int(rank_j))
    t = min(20, max(0, m)) / 20.0
    return SPEC_FACTOR_MIN + (SPEC_FACTOR_MAX - SPEC_FACTOR_MIN) * t


def _inhibition(
    ci: dict[str, Any],
    cj: dict[str, Any],
    matrix: list[list[float]],
) -> float:
    ai = _area_to_index((ci.get("area_ids") or [None])[0])
    aj = _area_to_index((cj.get("area_ids") or [None])[0])
    if ai < 0 or aj < 0 or ai >= len(matrix) or aj >= len(matrix[0]):
        return 0.0
    base = float(matrix[ai][aj])
    ri = int(ci.get("specificity_rank", 10))
    rj = int(cj.get("specificity_rank", 10))
    fac = _specificity_factor(ri, rj)
    return min(INHIB_MAX, base * fac)


def compile_h_total(
    concepts: list[dict[str, Any]],
    area_matrix: list[list[float]],
) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in concepts:
        cid = str(row.get("concept_id", ""))
        if not cid:
            continue
        by_id[cid] = row

    concept_index = sorted(by_id.keys())
    diagonal: dict[str, float] = {}
    for cid in concept_index:
        r = int(by_id[cid].get("specificity_rank", 10))
        diagonal[cid] = round(_diagonal_value(r), ROUND_DIGITS)

    edges: list[dict[str, Any]] = []
    n = len(concept_index)
    for i in range(n):
        for j in range(i + 1, n):
            ci = by_id[concept_index[i]]
            cj = by_id[concept_index[j]]
            coup = _coupling(ci, cj)
            inh = _inhibition(ci, cj, area_matrix)
            val = round(coup - inh, ROUND_DIGITS)
            if abs(val) < 1e-12 and coup <= 0.0 and inh <= 0.0:
                continue
            fi = (ci.get("family_ids") or [None])[0]
            fj = (cj.get("family_ids") or [None])[0]
            ai = (ci.get("area_ids") or [None])[0]
            aj = (cj.get("area_ids") or [None])[0]
            if fi and fj and str(fi) == str(fj):
                reason = "same_family"
            elif ai and aj and str(ai) == str(aj):
                reason = "same_area"
            else:
                reason = "cross_area"
            edges.append(
                {
                    "a": concept_index[i],
                    "b": concept_index[j],
                    "coupling": round(coup, ROUND_DIGITS),
                    "inhibition": round(inh, ROUND_DIGITS),
                    "value": val,
                    "reason": reason,
                }
            )

    return {
        "version": "v060",
        "matrix_id": "h_total_concepts",
        "space": "concept_id",
        "description": "Deterministic bounded semantic propagation operator over concept activations.",
        "build_rules": {
            "symmetric": True,
            "bounded_min": -1.0,
            "bounded_max": 1.0,
            "default_missing_edge": 0.0,
            "diagonal_semantics": "self_retention",
            "off_diagonal_positive": "semantic_coupling",
            "off_diagonal_negative": "competitive_inhibition",
        },
        "normalization": {
            "row_balance_target": 1.0,
            "clip_abs_value": 1.0,
            "post_build_symmetrize": True,
        },
        "concept_index": concept_index,
        "diagonal": diagonal,
        "edges": edges,
        "provenance": {
            "sources": [],
            "build_method": "deterministic_rule_compilation",
            "notes": "Built via tools/build_h_total_concepts.py; see provenance_inputs in build log.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline deterministic H_total from Dict B JSONL + area inhibition matrix.",
    )
    parser.add_argument(
        "--dict-b",
        type=Path,
        default=None,
        help="Dict B JSONL (default: dict_b_seed.jsonl; use --use-tfp-inputs for dict_b_tfp.jsonl)",
    )
    parser.add_argument(
        "--inhibition",
        type=Path,
        default=None,
        help="Area inhibition JSON (default: semantic_dynamics/area_inhibition_matrix_main_v1.json)",
    )
    parser.add_argument(
        "--use-tfp-inputs",
        action="store_true",
        help="Use dict_b_tfp.jsonl + tfp/area_inhibition_matrix_tfp.json (operator / calibration only).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Write compiled JSON here (default: outputs/semantic_dynamics/h_total_concepts.json)",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help=f"Also write {ASSET_PIN.relative_to(REPO_ROOT)} (review before commit).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write files.",
    )
    args = parser.parse_args()

    if args.use_tfp_inputs:
        dict_b = args.dict_b or DICT_B_TFP
        inhib = args.inhibition or INHIBITION_TFP
        print("warning: --use-tfp-inputs (TFP paths); coordinate with calibration boundary.", file=sys.stderr)
    else:
        dict_b = args.dict_b or DEFAULT_DICT_B
        inhib = args.inhibition or DEFAULT_INHIBITION_MAIN

    if not dict_b.is_file():
        print(f"error: missing {dict_b}", file=sys.stderr)
        return 2
    if not inhib.is_file():
        print(f"error: missing {inhib}", file=sys.stderr)
        return 2

    concepts = _load_dict_b(dict_b)
    _area_ids, matrix = _load_inhibition_matrix(inhib)
    payload = compile_h_total(concepts, matrix)
    prov = payload["provenance"]
    if isinstance(prov, dict):
        prov["sources"] = [str(dict_b.relative_to(REPO_ROOT)), str(inhib.relative_to(REPO_ROOT))]

    summary = {
        "concept_count": len(payload["concept_index"]),
        "edge_count": len(payload["edges"]),
        "dict_b": str(dict_b),
        "inhibition": str(inhib),
    }
    if args.dry_run:
        print(json.dumps({**summary, "diagonal_sample": dict(list(payload["diagonal"].items())[:4])}, indent=2))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if args.install:
        ASSET_PIN.parent.mkdir(parents=True, exist_ok=True)
        ASSET_PIN.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"installed {ASSET_PIN}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
