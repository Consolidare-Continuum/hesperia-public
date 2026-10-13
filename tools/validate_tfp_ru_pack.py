#!/usr/bin/env python3
# HESPERIA — RAD. RU TFP stack validation (Codex PHASE 8 + merge-aware).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
DA_FILES = [
    BASE / "dict_a" / "dict_a_tfp_ru_core.jsonl",
    BASE / "dict_a" / "dict_a_tfp_ru_variants.jsonl",
    BASE / "dict_a" / "dict_a_tfp_ru_speech.jsonl",
    BASE / "dict_a" / "dict_a_tfp_ru_negative.jsonl",
]
# Optional: corpus-aligned phrases (same merge order as DLCR pipeline tail).
DA_ALIGNED = BASE / "dict_a" / "dict_a_tfp_ru_aligned.jsonl"
STACK_B = BASE / "dict_b" / "dict_b_tfp_ru_v060.jsonl"
ANCH_PATH = BASE / "anchors" / "concept_hex_anchors_tfp.json"
MIN_LEXICAL_PER_ACTIVE = 3


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def merge_dict_b(paths: list[Path]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for p in paths:
        for row in load_jsonl(p):
            cid = row.get("concept_id")
            if cid and cid not in by_id:
                by_id[str(cid)] = row
    return [by_id[k] for k in sorted(by_id)]


def main() -> int:
    errs: list[str] = []
    stack_ids = {r["concept_id"] for r in load_jsonl(STACK_B)}
    dict_b = merge_dict_b(
        [
            BASE / "dict_b" / "dict_b_seed.jsonl",
            STACK_B,
            BASE / "dict_b" / "dict_b_tfp.jsonl",
        ]
    )
    concept_index = {r["concept_id"]: r for r in dict_b}
    anchors = json.loads(ANCH_PATH.read_text(encoding="utf-8")) if ANCH_PATH.exists() else {}

    dict_a: list[dict] = []
    for p in DA_FILES:
        dict_a.extend(load_jsonl(p))
    if DA_ALIGNED.exists():
        dict_a.extend(load_jsonl(DA_ALIGNED))

    ref_counts: Counter[str] = Counter()
    for row in dict_a:
        neg = row.get("negative_patterns") or []
        cids = row.get("candidate_concept_ids") or []
        if neg:
            continue
        if not cids:
            errs.append(f"Dict A active {row.get('entry_id')}: empty candidates without negative_patterns")
            continue
        for cid in cids:
            ref_counts[cid] += 1
            if cid not in concept_index:
                errs.append(f"Dict A {row.get('entry_id')}: unknown concept_id {cid!r}")

    for cid in sorted(stack_ids):
        r = concept_index.get(cid)
        if not r:
            errs.append(f"Stack concept {cid} missing from merged Dict B")
            continue
        if r.get("status") == "active":
            if not (r.get("definition") or "").strip():
                errs.append(f"Dict B {cid}: empty definition")
            if cid not in anchors:
                errs.append(f"Dict B {cid}: missing hex anchor")
            if ref_counts[cid] < MIN_LEXICAL_PER_ACTIVE:
                errs.append(
                    f"Dict B {cid}: only {ref_counts[cid]} active lexical row(s), need >= {MIN_LEXICAL_PER_ACTIVE}"
                )

    # Duplicates within merged list (should be unique by id)
    dup = [k for k, v in Counter(r["concept_id"] for r in dict_b).items() if v > 1]
    if dup:
        errs.append(f"duplicate concept_ids after merge: {dup[:20]}")

    raw_corpus = BASE / "dict_a" / "_raw" / "dict_a_ru_full_corpus.jsonl"
    if not raw_corpus.exists():
        # Large file; gitignored — absent in minimal CI clones. Full gate on dev/prod trees with assets.
        ci = os.environ.get("CI", "").strip().lower() in ("1", "true", "yes")
        skip = os.environ.get("HESPERIA_SKIP_RAW_DICT_A_CHECK", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if ci or skip:
            print(
                "WARNING: RAW dict_a corpus not in workspace (expected "
                f"{raw_corpus}); skipping RAW presence check.",
                file=sys.stderr,
            )
        else:
            errs.append(f"RAW archive missing (expected {raw_corpus})")

    if errs:
        for e in errs:
            print(f"ERROR: {e}")
        print(f"\nvalidate_tfp_ru_pack: FAIL ({len(errs)} issue(s))")
        return 1
    print(
        "validate_tfp_ru_pack: OK "
        f"(stack_concepts={len(stack_ids)}, active_dict_a_rows={len(dict_a)}, merged_b={len(dict_b)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
