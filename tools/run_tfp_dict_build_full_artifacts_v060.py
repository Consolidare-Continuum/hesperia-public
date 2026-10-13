#!/usr/bin/env python3
# HESPERIA — RAD. CODEX: RUN__TFP_DICT_BUILD_AND_EXPANSION__WITH_FULL_ARTIFACTS__V060
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Full TFP RU dictionary pipeline + mandatory human-inspection artifacts.

1. Build stack from ``research/_noone_local/2_cleaned/`` (RAW + active Dict A + v060 Dict B seed).
2. Merge Dict B: seed → v060 → existing ``dict_b_tfp.jsonl`` (first-wins by concept_id).
3. Controlled Dict B expansion (corpus clusters).
4. Write ``assets/data/engine_dynamics_v060/_artifacts/*.json`` and console summary.

Run:
  python3 tools/run_tfp_dict_build_full_artifacts_v060.py --write
  python3 tools/run_tfp_dict_build_full_artifacts_v060.py --write --skip-build   # artifacts + expand only
  python3 tools/run_tfp_dict_build_full_artifacts_v060.py --artifacts-only        # refresh views from disk
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "research" / "_noone_local" / "2_cleaned"
BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
ART = BASE / "_artifacts"
CORPORA = BASE / "corpora"
RAW_DIR = BASE / "dict_a" / "_raw"
DICT_A = BASE / "dict_a"
DICT_B = BASE / "dict_b"

SEED_B = DICT_B / "dict_b_seed.jsonl"
V060_B = DICT_B / "dict_b_tfp_ru_v060.jsonl"
DB_TFP = DICT_B / "dict_b_tfp.jsonl"

RAW_CORPUS = RAW_DIR / "dict_a_ru_full_corpus.jsonl"
RAW_TAGGED = RAW_DIR / "dict_a_ru_full_tagged.jsonl"
RAW_MAPPED = RAW_DIR / "dict_a_ru_mapped.jsonl"
CORE_PATH = DICT_A / "dict_a_tfp_ru_core.jsonl"
VARIANT_PATH = DICT_A / "dict_a_tfp_ru_variants.jsonl"
SPEECH_PATH = DICT_A / "dict_a_tfp_ru_speech.jsonl"
NEG_PATH = DICT_A / "dict_a_tfp_ru_negative.jsonl"

CONF_CORE_WEAK = 0.7  # aligned with build_ru_tfp_dictionary_stack.CONF_CORE


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge_dict_b_first_wins(paths: list[Path]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for p in paths:
        for row in load_jsonl(p):
            cid = row.get("concept_id")
            if cid and str(cid) not in by_id:
                by_id[str(cid)] = row
    return [by_id[k] for k in sorted(by_id)]


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def _load_tool_module(stem: str) -> Any:
    path = REPO / "tools" / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_build(write: bool) -> dict[str, Any]:
    if not SRC.is_dir():
        raise FileNotFoundError(f"Corpus source missing: {SRC}")
    mod = _load_tool_module("build_ru_tfp_dictionary_stack")
    return mod.run_pipeline(write=write)


def run_expand(write: bool) -> dict[str, Any]:
    mod = _load_tool_module("expand_dict_b_tfp_controlled")
    return mod.run(write=write)


def lexical_ref_counts(dict_a_rows: list[dict[str, Any]]) -> Counter[str]:
    c: Counter[str] = Counter()
    for row in dict_a_rows:
        if row.get("negative_patterns"):
            continue
        cids = row.get("candidate_concept_ids") or []
        if not cids:
            continue
        for cid in cids:
            c[str(cid)] += 1
    return c


def concept_examples_from_dict_a(
    concept_ids: list[str], dict_a_rows: list[dict[str, Any]], per_concept: int = 8
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {cid: [] for cid in concept_ids}
    want = set(concept_ids)
    for row in dict_a_rows:
        if row.get("negative_patterns"):
            continue
        for cid in row.get("candidate_concept_ids") or []:
            sc = str(cid)
            if sc not in want:
                continue
            if len(out[sc]) >= per_concept:
                continue
            for ex in row.get("examples") or []:
                if isinstance(ex, str) and ex.strip():
                    t = " ".join(ex.split())[:240]
                    if t and t not in out[sc]:
                        out[sc].append(t)
                if len(out[sc]) >= per_concept:
                    break
    return out


def collect_debug_artifacts(
    mapped: list[dict[str, Any]],
    core: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    speech: list[dict[str, Any]],
) -> tuple[list[dict], list[dict], list[dict]]:
    """conflicts, multi_candidate, weak_core."""
    by_nf_layer: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for name, rows in (("core", core), ("variants", variants), ("speech", speech)):
        for r in rows:
            nf = r.get("normalized_form")
            if not nf:
                continue
            cids = [str(x) for x in (r.get("candidate_concept_ids") or [])]
            by_nf_layer[str(nf)][name] = cids

    conflicts: list[dict[str, Any]] = []
    nfs = set(by_nf_layer.keys())
    for nf in sorted(nfs):
        layers = by_nf_layer[nf]
        if len(layers) < 2:
            continue
        sigs = {k: tuple(sorted(v)) for k, v in layers.items()}
        unique_vals = set(sigs.values())
        if len(unique_vals) > 1:
            conflicts.append(
                {
                    "normalized_form": nf,
                    "by_layer": {k: list(v) for k, v in layers.items()},
                    "reason": "candidate_concept_ids_differ_across_active_layers",
                }
            )

    multi_candidate: list[dict[str, Any]] = []
    for r in mapped:
        cids = r.get("candidate_concept_ids") or []
        if len(cids) <= 1:
            continue
        multi_candidate.append(
            {
                "phrase": r.get("normalized_form"),
                "freq": int(r.get("frequency") or 0),
                "candidate_concept_ids": [str(x) for x in cids],
                "confidence_hint": r.get("confidence_hint"),
                "class_hint": r.get("class_hint"),
            }
        )
    multi_candidate.sort(key=lambda x: (-x["freq"], str(x["phrase"])))
    multi_candidate = multi_candidate[:2500]

    mapped_conf = {str(r.get("normalized_form")): float(r.get("confidence_hint") or 0) for r in mapped}
    weak_core: list[dict[str, Any]] = []
    for r in core:
        nf = str(r.get("normalized_form") or "")
        conf = mapped_conf.get(nf, 0.0)
        if conf < CONF_CORE_WEAK:
            weak_core.append(
                {
                    "entry_id": r.get("entry_id"),
                    "normalized_form": nf,
                    "candidate_concept_ids": r.get("candidate_concept_ids"),
                    "mapped_confidence_hint": conf,
                    "reason": f"mapped_confidence_below_{CONF_CORE_WEAK}",
                }
            )

    return conflicts, multi_candidate, weak_core


def write_all_artifacts(
    expansion_report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Populate _artifacts/ from current on-disk JSONL (post build/expand)."""
    ART.mkdir(parents=True, exist_ok=True)

    raw_corpus = load_jsonl(RAW_CORPUS)
    tagged = load_jsonl(RAW_TAGGED)
    mapped = load_jsonl(RAW_MAPPED)
    core = load_jsonl(CORE_PATH)
    variants = load_jsonl(VARIANT_PATH)
    speech = load_jsonl(SPEECH_PATH)
    negative = load_jsonl(NEG_PATH)
    dict_b = load_jsonl(DB_TFP)

    top_phrases = [
        {"phrase": r.get("normalized_form", ""), "freq": int(r.get("frequency") or 0)}
        for r in sorted(raw_corpus, key=lambda x: (-int(x.get("frequency") or 0), str(x.get("normalized_form"))))[
            :5000
        ]
    ]
    save_json(ART / "top_phrases.json", top_phrases)

    save_json(ART / "sample_core.json", core[:50])
    save_json(ART / "sample_speech.json", speech[:50])

    unmapped: list[dict[str, Any]] = []
    for r in mapped:
        cids = r.get("candidate_concept_ids") or []
        if cids:
            continue
        unmapped.append(
            {
                "phrase": r.get("normalized_form", ""),
                "freq": int(r.get("frequency") or 0),
                "class_hint": r.get("class_hint", ""),
            }
        )
    unmapped.sort(key=lambda x: (-x["freq"], x["phrase"]))
    save_json(ART / "unmapped_entries.json", unmapped[:8000])

    da_active = core + variants + speech
    ref_counts = lexical_ref_counts(da_active)
    concepts_summary = []
    for row in dict_b:
        cid = str(row.get("concept_id", ""))
        concepts_summary.append(
            {
                "concept_id": cid,
                "label": row.get("preferred_label", ""),
                "lexical_support_count": int(ref_counts.get(cid, 0)),
            }
        )
    concepts_summary.sort(key=lambda x: (-x["lexical_support_count"], x["concept_id"]))
    save_json(ART / "concepts_summary.json", concepts_summary)

    tfp_ids = [str(r["concept_id"]) for r in dict_b if str(r.get("concept_id", "")).startswith("TFP_")]
    examples = concept_examples_from_dict_a(tfp_ids, da_active + load_jsonl(RAW_MAPPED), per_concept=6)
    save_json(ART / "concept_examples.json", examples)

    audit = (expansion_report or {}).get("_artifact_cluster_audit") or {}
    accepted = audit.get("accepted") or []
    concept_clusters = [
        {
            "cluster_id": x.get("cluster_id"),
            "top_phrases": x.get("top_phrases") or [],
            "size": x.get("size"),
            "mapped_to": x.get("mapped_to"),
            "action": x.get("action"),
        }
        for x in accepted
    ]
    save_json(ART / "concept_clusters.json", concept_clusters)

    rejected = audit.get("rejected") or []
    save_json(ART / "rejected_clusters.json", rejected)

    neg_out = [
        {
            "entry_id": r.get("entry_id"),
            "phrase": r.get("normalized_form"),
            "surface_form": r.get("surface_form"),
            "negative_patterns": r.get("negative_patterns"),
            "candidate_concept_ids": r.get("candidate_concept_ids"),
        }
        for r in negative
    ]
    save_json(ART / "negative_matches.json", neg_out)

    total_refs = sum(int(ref_counts.get(str(r.get("concept_id")), 0)) for r in dict_b)
    avg_sup = (total_refs / len(dict_b)) if dict_b else 0.0
    build_summary = {
        "raw_entries": len(raw_corpus),
        "tagged_entries": len(tagged),
        "mapped_entries": len(mapped),
        "core_entries": len(core),
        "variant_entries": len(variants),
        "speech_entries": len(speech),
        "negative_entries": len(negative),
        "concept_count": len(dict_b),
        "avg_lexical_support_per_concept": round(avg_sup, 4),
    }
    br_path = BASE / "_build_report.json"
    if br_path.exists():
        build_summary["_build_report_embed"] = json.loads(br_path.read_text(encoding="utf-8"))
    if expansion_report:
        build_summary["_dict_b_expansion_embed"] = {
            k: expansion_report[k]
            for k in expansion_report
            if not k.startswith("_artifact")
        }
    save_json(ART / "build_summary.json", build_summary)

    conflicts, multi_c, weak_c = collect_debug_artifacts(mapped, core, variants, speech)
    save_json(ART / "conflicts.json", conflicts)
    save_json(ART / "multi_candidate_entries.json", multi_c)
    save_json(ART / "weak_core_entries.json", weak_c)

    return {
        "artifacts_dir": str(ART),
        "build_summary": build_summary,
        "unmapped_count": len(unmapped),
        "concept_clusters_count": len(concept_clusters),
        "rejected_cluster_records": len(rejected),
    }


def console_report() -> None:
    raw_corpus = load_jsonl(RAW_CORPUS)
    core = load_jsonl(CORE_PATH)
    variants = load_jsonl(VARIANT_PATH)
    speech = load_jsonl(SPEECH_PATH)
    mapped = load_jsonl(RAW_MAPPED)
    dict_b = load_jsonl(DB_TFP)
    da_active = core + variants + speech
    ref_counts = lexical_ref_counts(da_active)

    top20 = sorted(raw_corpus, key=lambda x: (-int(x.get("frequency") or 0), str(x.get("normalized_form"))))[:20]
    print("\n=== TOP 20 PHRASES (raw corpus) ===")
    for r in top20:
        print(f"  {int(r.get('frequency') or 0):6d}  {r.get('normalized_form')}")

    top_concepts = sorted(
        ((cid, n) for cid, n in ref_counts.items() if n > 0),
        key=lambda x: -x[1],
    )[:10]
    print("\n=== TOP 10 CONCEPTS (by active Dict A support) ===")
    idx = {r["concept_id"]: r for r in dict_b}
    for cid, n in top_concepts:
        lab = idx.get(cid, {}).get("preferred_label", "")
        print(f"  {n:5d}  {cid}  ({lab})")

    rng = random.Random(42)
    sp_sample = speech[:] if speech else []
    rng.shuffle(sp_sample)
    print("\n=== 10 RANDOM SPEECH ENTRIES (seed=42) ===")
    for r in sp_sample[:10]:
        print(f"  {r.get('entry_id')}: {r.get('normalized_form')} -> {r.get('candidate_concept_ids')}")

    um = [
        r
        for r in mapped
        if not (r.get("candidate_concept_ids") or [])
    ]
    um.sort(key=lambda x: -int(x.get("frequency") or 0))
    print("\n=== 10 UNMAPPED HIGH-FREQ (mapped layer) ===")
    for r in um[:10]:
        print(f"  {int(r.get('frequency') or 0):6d}  {r.get('normalized_form')}  [{r.get('class_hint')}]")

    cc_path = ART / "concept_clusters.json"
    clusters = json.loads(cc_path.read_text(encoding="utf-8")) if cc_path.exists() else []
    print("\n=== 5 CONCEPT CLUSTERS (expansion) ===")
    for c in clusters[:5]:
        print(f"  {c.get('mapped_to')} <= {c.get('cluster_id')}  phrases={c.get('top_phrases', [])[:4]}...")


def main() -> int:
    ap = argparse.ArgumentParser(description="TFP dict full build + expansion + _artifacts/")
    ap.add_argument("--write", action="store_true", help="Execute build/expand writes (not dry-run)")
    ap.add_argument("--skip-build", action="store_true", help="Skip stack builder (use existing RAW/ACTIVE)")
    ap.add_argument("--skip-expand", action="store_true", help="Skip Dict B expansion step")
    ap.add_argument(
        "--artifacts-only",
        action="store_true",
        help="Only regenerate _artifacts/*.json from current data (no build, no expand)",
    )
    args = ap.parse_args()

    expansion_report: dict[str, Any] | None = None

    if args.artifacts_only:
        rep_path = BASE / "_dict_b_expansion_report.json"
        expansion_report = (
            json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.exists() else None
        )
        meta = write_all_artifacts(expansion_report)
        console_report()
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    if not args.skip_build:
        if not args.write:
            print("Dry-run: would run build_ru_tfp_dictionary_stack (pass --write).", file=sys.stderr)
        else:
            print("Running build_ru_tfp_dictionary_stack.py --write ...", file=sys.stderr)
            run_build(write=True)

    if args.write and not args.artifacts_only:
        print("Merging Dict B (seed → v060 → dict_b_tfp, first-wins) ...", file=sys.stderr)
        merged = merge_dict_b_first_wins([SEED_B, V060_B, DB_TFP])
        save_jsonl(DB_TFP, merged)

    if not args.skip_expand:
        if not args.write:
            print("Dry-run: would run expand_dict_b_tfp_controlled (pass --write).", file=sys.stderr)
            expansion_report = run_expand(write=False)
        else:
            print("Running expand_dict_b_tfp_controlled.py --write ...", file=sys.stderr)
            expansion_report = run_expand(write=True)
    else:
        rep_path = BASE / "_dict_b_expansion_report.json"
        expansion_report = (
            json.loads(rep_path.read_text(encoding="utf-8"))
            if rep_path.exists()
            else run_expand(write=False)
        )

    meta = write_all_artifacts(expansion_report)
    console_report()
    print(json.dumps(meta, ensure_ascii=False, indent=2))

    if not args.write:
        print("\nDry run complete. Re-run with --write to emit/update all files.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
