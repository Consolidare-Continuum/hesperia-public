#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Phase 5 — Validate Dict A and Dict B before freeze.
- All side_id in Dict A exist in canonical side set (0..N-1 or allowed strings).
- No family_id or area_id inside Dict A.
- All aliases resolve to exactly one side_id (no duplicate alias across sides).
- Optional: checksum output to curated/checksums_v1.json.
Run: python3 lexicon/validation/validate_lexical.py [--curated dir] [--canonical-max N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LEX_ROOT = Path(__file__).resolve().parent.parent
CURATED = LEX_ROOT / "curated"
CANONICAL_SIDES_MAX = 432000  # 12 areas * 24 fam * 250 hex * 6 sides
WEIGHT_CAP_DEFAULT = 1.0  # Dict A: weight must be in (0, cap]; override with --weight-cap to match guard_config


def _norm_alias(s: str) -> str:
    """Normalize for duplicate detection: lowercase, strip, collapse internal space."""
    return " ".join(s.lower().strip().split())


def load_canonical_side_set(max_sides: int) -> set[int | str]:
    """Canonical set: 0..max_sides-1. String side_id allowed only if side_id_format permits."""
    return set(range(max_sides))


def validate_dict_a(path: Path, canonical: set[int | str], side_id_format: str = "int", weight_cap: float = WEIGHT_CAP_DEFAULT) -> list[str]:
    errs = []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for lemma, entries in data.items():
        if lemma.startswith("_"):
            continue
        if not isinstance(entries, list):
            errs.append(f"Dict A '{lemma}': value must be list of {{side_id, weight, map_code}}")
            continue
        if len(entries) > 3:
            errs.append(f"Dict A '{lemma}': max 3 seeds per lemma (hard rule), got {len(entries)}")
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                errs.append(f"Dict A '{lemma}'[{i}]: entry must be object")
                continue
            sid = e.get("side_id")
            w = e.get("weight")
            if sid is None:
                errs.append(f"Dict A '{lemma}'[{i}]: missing side_id")
            else:
                if side_id_format == "int":
                    try:
                        sid_int = int(sid)
                        if sid_int not in canonical:
                            errs.append(f"Dict A '{lemma}'[{i}]: side_id {sid} not in canonical set")
                    except (TypeError, ValueError):
                        errs.append(f"Dict A '{lemma}'[{i}]: side_id must be integer (side_id_format=int)")
                else:
                    if sid not in canonical:
                        errs.append(f"Dict A '{lemma}'[{i}]: side_id not in canonical set")
            if "family_id" in e or "area_id" in e or "family" in e or "area" in e:
                errs.append(f"Dict A '{lemma}'[{i}]: must not contain family_id/area_id/family/area")
            if w is not None:
                if not isinstance(w, (int, float)):
                    errs.append(f"Dict A '{lemma}'[{i}]: weight must be number")
                elif w <= 0 or w > weight_cap:
                    errs.append(f"Dict A '{lemma}'[{i}]: weight must be in (0, {weight_cap}] (positive, capped)")
    return errs


def validate_dict_b(path: Path, canonical: set[int | str], side_id_format: str = "int") -> list[str]:
    errs = []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    alias_to_side: dict[str, list[str | int]] = {}
    for side_key, obj in data.items():
        if side_key.startswith("_"):
            continue
        if not isinstance(obj, dict):
            errs.append(f"Dict B '{side_key}': value must be {{canonical_lemma, aliases}}")
            continue
        if side_id_format == "int":
            try:
                sid_int = int(side_key)
                if sid_int not in canonical:
                    errs.append(f"Dict B side_id {side_key} not in canonical set")
            except (TypeError, ValueError):
                errs.append(f"Dict B side_id '{side_key}' must be integer (side_id_format=int)")
        canonical_lemma = (obj.get("canonical_lemma") or "").strip().lower()
        has_grade_a_canonical = False
        for a in obj.get("aliases", []):
            if isinstance(a, dict):
                al_raw = a.get("alias", "")
                grade = a.get("grade", "")
                al = _norm_alias(al_raw)
                if al:
                    alias_to_side.setdefault(al, []).append(side_key)
                    if grade == "A" and al == _norm_alias(canonical_lemma):
                        has_grade_a_canonical = True
            elif isinstance(a, str):
                al = _norm_alias(a)
                if al:
                    alias_to_side.setdefault(al, []).append(side_key)
        if canonical_lemma and not has_grade_a_canonical:
            errs.append(f"Dict B '{side_key}': canonical_lemma '{canonical_lemma}' must appear among aliases with grade A")
    for al, sides in alias_to_side.items():
        if len(sides) > 1:
            errs.append(f"Dict B: alias '{al}' (normalized) resolves to multiple sides: {sides}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated", type=Path, default=CURATED)
    ap.add_argument("--canonical-max", type=int, default=CANONICAL_SIDES_MAX)
    ap.add_argument("--side-id-format", choices=("int", "string"), default="int")
    ap.add_argument("--weight-cap", type=float, default=WEIGHT_CAP_DEFAULT, help="Dict A weight upper bound (match guard_config if set)")
    args = ap.parse_args()

    canonical = load_canonical_side_set(args.canonical_max)
    all_errs = []

    # Default Dict A filenames: v0.4.1.1 (LEGACY label); fallback v0.4.1 (v1) deprecated — not system_version.
    a_path = args.curated / "A_CORE_STAR_MAP_v0_4_1_1.json"
    if not a_path.exists():
        a_path = args.curated / "A_CORE_STAR_MAP_v1.json"
    b_path = args.curated / "B_SURFACE_LEX_FIELD_v1.json"

    if a_path.exists():
        all_errs.extend(validate_dict_a(a_path, canonical, side_id_format=args.side_id_format, weight_cap=args.weight_cap))
    else:
        all_errs.append("A_CORE_STAR_MAP_v0_4_1_1.json (or A_CORE_STAR_MAP_v1.json) not found")
    if b_path.exists():
        all_errs.extend(validate_dict_b(b_path, canonical, side_id_format=args.side_id_format))
    else:
        all_errs.append("B_SURFACE_LEX_FIELD_v1.json not found")

    if all_errs:
        for e in all_errs:
            print("VALIDATE_ERR:", e, file=sys.stderr)
        return 1

    # Checksums (Dict A file v0.4.1.1 preferred, v1 deprecated — LEGACY asset naming)
    checksums = {}
    for name in ("A_CORE_STAR_MAP_v0_4_1_1.json", "A_CORE_STAR_MAP_v1.json", "B_SURFACE_LEX_FIELD_v1.json"):
        p = args.curated / name
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            checksums[name] = h
    out = args.curated / "checksums_v1.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"checksums": checksums, "canonical_max": args.canonical_max}, f, indent=2)

    # Freeze record (cryptographic): SHA256 of A, B, guard_config; source refs; repo commit
    hesperia_root = LEX_ROOT.parent
    guard_path = hesperia_root / "assets" / "config" / "guard_config_v1.json"
    repo_commit = None
    try:
        import subprocess
        repo_root = hesperia_root  # repository root
        if (repo_root / ".git").exists():
            repo_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
            ).strip()
    except Exception:
        pass
    freeze = {
        "version": "lexical-stack-v1.0",
        "tag": "lexical-stack-v1.0",
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "repo_commit": repo_commit,
        "sha256": {
            "A_CORE_STAR_MAP_v0_4_1_1.json": checksums.get("A_CORE_STAR_MAP_v0_4_1_1.json"),
            "A_CORE_STAR_MAP_v1.json": checksums.get("A_CORE_STAR_MAP_v1.json"),
            "B_SURFACE_LEX_FIELD_v1.json": checksums.get("B_SURFACE_LEX_FIELD_v1.json"),
            "guard_config_v1.json": hashlib.sha256(guard_path.read_bytes()).hexdigest() if guard_path.exists() else None,
        },
        "sources": {
            "oewn": os.environ.get("OEWN_TAG", "v2023.1"),
            "scowl": os.environ.get("SCOWL_VERSION", "2020.12.07"),
            "wiktionary": os.environ.get("WIKT_DUMP_DATE", "latest"),
        },
        "rules": [
            "No automatic updates. All updates require version bump, change log, CI pass.",
            "Dict A: side_id only; no family_id/area_id. Max 3 seeds per lemma; weight in (0, cap].",
            "Dict B: alias grades A/B/C only; canonical_lemma must appear as grade A; no duplicate alias after normalization.",
        ],
    }
    freeze_path = args.curated / "FREEZE_RECORD_v1.json"
    with open(freeze_path, "w", encoding="utf-8") as f:
        json.dump(freeze, f, indent=2)
    print("Validation OK. Checksums written to", out, "; freeze record to", freeze_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
