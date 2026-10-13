#!/usr/bin/env python3
"""Regression gate for DLCR corpora (multi-suite)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.lexical.matcher import match_dict_a
from core.lexical.normalization import normalize_text
from core.resolver.resolver import resolve_hit

BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
SUITES: list[tuple[str, list[Path], Path, Path]] = [
    (
        "seed_en",
        [BASE / "dict_a" / "dict_a_seed.jsonl"],
        BASE / "dict_b" / "dict_b_seed.jsonl",
        BASE / "corpora" / "gold_spans.jsonl",
    ),
    (
        "seed_en",
        [BASE / "dict_a" / "dict_a_seed.jsonl"],
        BASE / "dict_b" / "dict_b_seed.jsonl",
        BASE / "corpora" / "ambiguity_seed.jsonl",
    ),
    (
        "seed_en",
        [BASE / "dict_a" / "dict_a_seed.jsonl"],
        BASE / "dict_b" / "dict_b_seed.jsonl",
        BASE / "corpora" / "overlap_seed.jsonl",
    ),
    (
        "tfp_ru",
        [
            BASE / "dict_a" / "dict_a_tfp.jsonl",
            BASE / "dict_a" / "dict_a_tfp_ru_core.jsonl",
            BASE / "dict_a" / "dict_a_tfp_ru_variants.jsonl",
            BASE / "dict_a" / "dict_a_tfp_ru_speech.jsonl",
            BASE / "dict_a" / "dict_a_tfp_ru_negative.jsonl",
            BASE / "dict_a" / "dict_a_tfp_ru_aligned.jsonl",
        ],
        BASE / "dict_b" / "dict_b_tfp.jsonl",
        BASE / "corpora" / "gold_tfp_ru.jsonl",
    ),
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def merge_dict_a_files(paths: list[Path]) -> list[dict]:
    """Same merge policy as ``core.engine.lexical_concept.pipeline._merge_dict_a``."""
    rows: list[dict] = []
    seen_nf: set[str] = set()
    for p in paths:
        for row in load_jsonl(p):
            if row.get("negative_patterns"):
                rows.append(row)
                continue
            nf = row.get("normalized_form")
            if not nf or nf in seen_nf:
                continue
            seen_nf.add(nf)
            rows.append(row)
    return rows


def run_suite(
    suite_name: str,
    dict_a_paths: list[Path],
    dict_b_path: Path,
    gold_path: Path,
) -> list[str]:
    dict_a = merge_dict_a_files(dict_a_paths) if len(dict_a_paths) > 1 else load_jsonl(dict_a_paths[0])
    dict_b = load_jsonl(dict_b_path)
    concept_index = {row["concept_id"]: row for row in dict_b}
    gold_rows = load_jsonl(gold_path)
    errors: list[str] = []
    for row in gold_rows:
        text = row["text"]
        cid = row.get("corpus_id") or suite_name
        expected = {item["span"]: item["winner"] for item in row["spans"]}
        normalized = normalize_text(text)
        hits, _ = match_dict_a(normalized["canonical_text"], dict_a)
        actual: dict[str, str | None] = {}
        for hit in hits:
            resolved = resolve_hit(
                hit,
                concept_index,
                mode="clinical_speech",
                canonical_text=normalized["canonical_text"],
            )
            actual[hit.matched_text] = resolved["winning_concept_id"]
        for span, expected_winner in expected.items():
            got = actual.get(span)
            if got != expected_winner:
                errors.append(
                    f"[{cid}/{suite_name}] text={text!r} span={span!r} expected={expected_winner!r} got={got!r}"
                )
    return errors


def main() -> int:
    all_errs: list[str] = []
    for suite_name, da_paths, db, gold in SUITES:
        if not db.exists() or not gold.exists() or any(not p.exists() for p in da_paths):
            print(f"SKIP suite missing files: {suite_name} {da_paths} {db} {gold}")
            continue
        all_errs.extend(run_suite(suite_name, da_paths, db, gold))
    if all_errs:
        for err in all_errs:
            print(f"ERROR: {err}")
        print(f"DLCR regression failed: {len(all_errs)} mismatch(es)")
        return 1
    print("DLCR regression OK (all corpora)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
