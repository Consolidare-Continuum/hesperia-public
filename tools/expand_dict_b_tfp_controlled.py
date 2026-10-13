#!/usr/bin/env python3
# HESPERIA — RAD. CODEX: EXPAND__DICT_B_TFP__FROM_CORPUS_AND_THEORY__V060
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Controlled Dict B expansion: cluster mapped lexical rows → merge into existing
or append new TFP_* concepts with caps, deterministic filters, and a JSON report.

Read:
  dict_a/_raw/dict_a_ru_mapped.jsonl
  dict_a/dict_a_tfp_ru_core.jsonl, dict_a_tfp_ru_variants.jsonl
  dict_b/dict_b_tfp.jsonl (read/update; preserves B_A10_* and prior rows)

Write:
  dict_b/dict_b_tfp.jsonl (full rewrite)
  _dict_b_expansion_report.json

Run:  python3 tools/expand_dict_b_tfp_controlled.py --write
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
MAPPED = BASE / "dict_a" / "_raw" / "dict_a_ru_mapped.jsonl"
SENTENCES = BASE / "corpora" / "tfp_ru_sentences.jsonl"
CORE = BASE / "dict_a" / "dict_a_tfp_ru_core.jsonl"
VARIANTS = BASE / "dict_a" / "dict_a_tfp_ru_variants.jsonl"
DB_TFP = BASE / "dict_b" / "dict_b_tfp.jsonl"
REPORT_PATH = BASE / "_dict_b_expansion_report.json"

VER = "v0.6.0_tfp_expand"

# Mapped corpus may reference shorthand TFP ids; map to sealed Dict B concept_ids.
CORPUS_CONCEPT_ALIASES: dict[str, str] = {
    "TFP_DEVALUATION": "TFP_PRIMITIVE_DEVALUATION",
    "TFP_IDEALIZATION": "TFP_PRIMITIVE_IDEALIZATION",
    "TFP_OBJECT_RELATIONS": "TFP_REPRESENTATION_OBJECT",
    "TFP_AFFECT_INSTABILITY": "TFP_AFFECTIVE_STORMS",
    "TFP_POLARIZATION": "TFP_SPLITTING",
}

# --- Calibration (tight = no explosion) ---
MAX_NEW_CONCEPTS = 45
MAX_REJECTED_CLUSTER_RECORDS = 400
MIN_CLUSTER_ENTRIES = 3
MIN_CLUSTER_FREQ_SUM = 14
MIN_COOC = 2
MERGE_TOKEN_OVERLAP = 0.52
MAX_ALT_MERGE = 12
MIN_MAPPED_FREQ = 3
MIN_CONFIDENCE = 0.34

RU_STOP = frozenset(
    """
    и в во не на с со к у я а но или же ли бы то что это как от по за
    из для при над под об ко до при все ещё еще их его ее её им них
    мы вы они он она оно был была были быть будет который которая
    """.split()
)

TOKEN = re.compile(r"[а-яёa-z0-9]+", re.I)


def tokens(s: str) -> frozenset[str]:
    return frozenset(t.lower() for t in TOKEN.findall(s) if len(t) > 1 and t.lower() not in RU_STOP)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    u = len(a & b)
    return u / len(a | b)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def primary_cid(row: dict[str, Any]) -> str | None:
    cids = row.get("candidate_concept_ids") or []
    return str(cids[0]) if cids else None


def resolve_corpus_concept_id(raw_id: str | None, index: dict[str, dict]) -> str | None:
    """Map alias or verify id exists in Dict B (no invented ids in relations)."""
    if not raw_id:
        return None
    rid = str(raw_id)
    if rid in index:
        return rid
    alt = CORPUS_CONCEPT_ALIASES.get(rid)
    if alt and alt in index:
        return alt
    return None


def load_cooccurrence(mapped_by_nf: dict[str, dict], sentence_path: Path) -> Counter[tuple[str, str]]:
    """Co-occurring normalized_forms in same sentence (substring match)."""
    co: Counter[tuple[str, str]] = Counter()
    if not sentence_path.exists():
        return co
    nfs_sorted = sorted(mapped_by_nf.keys(), key=len, reverse=True)
    for line in sentence_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            text = (obj.get("text") or "").lower()
        except json.JSONDecodeError:
            continue
        hits: list[str] = []
        for nf in nfs_sorted:
            if nf in text:
                hits.append(nf)
        hits = sorted(set(hits))[:40]
        for i, a in enumerate(hits):
            for b in hits[i + 1 :]:
                k = (a, b) if a < b else (b, a)
                co[k] += 1
    return co


def _parent_cluster_key(row: dict[str, Any], concept_index: dict[str, dict]) -> str | None:
    raw = primary_cid(row)
    if not raw:
        return None
    return resolve_corpus_concept_id(raw, concept_index) or raw


def build_clusters(
    mapped: list[dict[str, Any]], concept_index: dict[str, dict]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Union-find by co-parent + jaccard + co-occurrence.

    Returns (accepted_clusters, rejected_pre_expand) where rejects are
    union-find groups that failed size/frequency gates (capped list for artifacts).
    """
    rows = [
        r
        for r in mapped
        if (r.get("candidate_concept_ids") or [])
        and float(r.get("confidence_hint") or 0) >= MIN_CONFIDENCE
        and int(r.get("frequency") or 0) >= MIN_MAPPED_FREQ
        and (r.get("class_hint") or "") != "noise"
    ]
    by_nf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        nf = r.get("normalized_form")
        if nf:
            by_nf[str(nf)].append(r)
    nf_keys = list(by_nf.keys())
    cooc = load_cooccurrence({k: by_nf[k][0] for k in nf_keys}, SENTENCES)
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    nfs = nf_keys
    for i, a in enumerate(nfs):
        ta = tokens(a)
        pa = _parent_cluster_key(by_nf[a][0], concept_index)
        if not pa:
            continue
        for b in nfs[i + 1 :]:
            pb = _parent_cluster_key(by_nf[b][0], concept_index)
            if pa != pb:
                continue
            tb = tokens(b)
            if jaccard(ta, tb) >= 0.38:
                union(a, b)
            k = (a, b) if a < b else (b, a)
            if cooc[k] >= MIN_COOC:
                union(a, b)

    groups: dict[str, list[str]] = defaultdict(list)
    for nf in nfs:
        groups[find(nf)].append(nf)

    clusters: list[dict[str, Any]] = []
    rejected_pre: list[dict[str, Any]] = []

    def _nf_freq(nf: str) -> int:
        return max(int(e.get("frequency") or 0) for e in by_nf[nf])

    for root, members in sorted(groups.items(), key=lambda x: x[0]):
        entries = []
        for m in members:
            entries.extend(by_nf[m])
        freq_sum = sum(int(e.get("frequency") or 0) for e in entries)
        top_preview = sorted(members, key=lambda nf: (-_nf_freq(nf), nf))[:8]
        if len(members) < MIN_CLUSTER_ENTRIES:
            if len(rejected_pre) < MAX_REJECTED_CLUSTER_RECORDS:
                rejected_pre.append(
                    {
                        "cluster_id": f"CLU_{root[:24]}_{len(members)}",
                        "top_phrases": top_preview,
                        "size": len(members),
                        "distinct_entries": len(entries),
                        "frequency_sum": freq_sum,
                        "reason": f"too_few_member_phrases_need_{MIN_CLUSTER_ENTRIES}",
                    }
                )
            continue
        if freq_sum < MIN_CLUSTER_FREQ_SUM:
            if len(rejected_pre) < MAX_REJECTED_CLUSTER_RECORDS:
                rejected_pre.append(
                    {
                        "cluster_id": f"CLU_{root[:24]}_{len(members)}",
                        "top_phrases": top_preview,
                        "size": len(members),
                        "distinct_entries": len(entries),
                        "frequency_sum": freq_sum,
                        "reason": f"frequency_sum_below_{MIN_CLUSTER_FREQ_SUM}",
                    }
                )
            continue
        top_phrases = sorted(members, key=lambda nf: (-_nf_freq(nf), nf))[:12]
        clusters.append(
            {
                "cluster_id": f"CLU_{root[:24]}_{len(members)}",
                "entries": entries,
                "top_phrases": top_phrases,
                "frequency_sum": freq_sum,
                "primary_parent": _parent_cluster_key(by_nf[members[0]][0], concept_index),
            }
        )
    clusters.sort(key=lambda c: (-c["frequency_sum"], c["cluster_id"]))
    return clusters, rejected_pre


def concept_signature(concept: dict[str, Any]) -> frozenset[str]:
    parts: list[str] = []
    parts.append(concept.get("preferred_label") or "")
    parts.extend(concept.get("alt_labels") or [])
    parts.append(concept.get("definition") or "")
    bag: set[str] = set()
    for p in parts:
        bag |= tokens(p)
    return frozenset(bag)


def cluster_signature(phrases: list[str]) -> frozenset[str]:
    bag: set[str] = set()
    for p in phrases:
        bag |= tokens(p)
    return frozenset(bag)


def is_generic_cluster(phrases: list[str]) -> bool:
    """Reject if mostly stopwords / too short."""
    if not phrases:
        return True
    toks = []
    for p in phrases[:5]:
        toks.extend(TOKEN.findall(p))
    if len(toks) < 6:
        return True
    good = sum(1 for t in toks if t.lower() not in RU_STOP and len(t) > 2)
    return good < max(4, len(toks) // 3)


def pick_family_area(parent_id: str | None, index: dict[str, dict]) -> tuple[list[str], list[str]]:
    resolved = resolve_corpus_concept_id(parent_id, index)
    if resolved:
        p = index[resolved]
        return list(p.get("family_ids") or ["F5"]), list(p.get("area_ids") or ["A3"])
    return ["F5"], ["A3"]


def _next_cluster_index(existing_rows: list[dict[str, Any]]) -> int:
    m = 0
    for r in existing_rows:
        cid = r.get("concept_id") or ""
        mm = re.match(r"^TFP_CLUSTER_(\d+)$", cid)
        if mm:
            m = max(m, int(mm.group(1)))
    return m


def _english_bundle_label(parent_id: str | None, index: dict[str, dict], idx: int) -> str:
    if parent_id and parent_id in index:
        pl = (index[parent_id].get("preferred_label") or "").strip()
        if pl:
            return f"Corpus lexical bundle ({pl})"
    return f"Corpus TFP lexical bundle {idx}"


def run(*, write: bool) -> dict[str, Any]:
    mapped = load_jsonl(MAPPED)
    raw_existing = load_jsonl(DB_TFP)
    stripped_clusters = sum(
        1
        for r in raw_existing
        if str(r.get("concept_id", "")).startswith("TFP_CLUSTER_")
    )
    # Idempotent re-build: drop prior automated corpus clusters, then regenerate.
    existing_rows = [
        r for r in raw_existing if not str(r.get("concept_id", "")).startswith("TFP_CLUSTER_")
    ]
    index = {r["concept_id"]: r for r in existing_rows}

    clusters, rejected_pre_expand = build_clusters(mapped, index)
    artifact_rejected: list[dict[str, Any]] = list(rejected_pre_expand)
    artifact_accepted: list[dict[str, Any]] = []

    generic_reject = 0
    valid: list[dict[str, Any]] = []
    for c in clusters:
        if is_generic_cluster(c["top_phrases"]):
            generic_reject += 1
            artifact_rejected.append(
                {
                    "cluster_id": c["cluster_id"],
                    "top_phrases": c["top_phrases"][:8],
                    "size": len(c["entries"]),
                    "frequency_sum": c["frequency_sum"],
                    "reason": "generic_or_stopword_heavy_cluster",
                }
            )
            continue
        valid.append(c)

    merged_into = 0
    new_concepts: list[dict[str, Any]] = []
    new_idx = _next_cluster_index(existing_rows)
    skipped_empty = 0
    skipped_cap = 0
    for c in valid:
        sig = cluster_signature(c["top_phrases"])
        if not sig:
            skipped_empty += 1
            artifact_rejected.append(
                {
                    "cluster_id": c["cluster_id"],
                    "top_phrases": c["top_phrases"][:8],
                    "size": len(c["entries"]),
                    "frequency_sum": c["frequency_sum"],
                    "reason": "empty_token_signature_after_stopword_filter",
                }
            )
            continue
        best_id = None
        best_ov = 0.0
        for cid, row in index.items():
            if cid.startswith("B_"):
                continue
            ov = jaccard(sig, concept_signature(row))
            if ov > best_ov:
                best_ov = ov
                best_id = cid
        if best_id and best_ov >= MERGE_TOKEN_OVERLAP:
            row = index[best_id]
            alts = list(row.get("alt_labels") or [])
            for ph in c["top_phrases"][:MAX_ALT_MERGE]:
                if ph not in alts and ph not in (row.get("preferred_label") or ""):
                    alts.append(ph)
            row["alt_labels"] = alts[:24]
            rc = set(row.get("related_concept_ids") or [])
            for e in c["entries"]:
                pid = resolve_corpus_concept_id(primary_cid(e), index)
                if pid and pid != best_id:
                    rc.add(pid)
            row["related_concept_ids"] = sorted(rc)[:16]
            clues = list(row.get("resolver_clues") or [])
            for t in list(sig)[:8]:
                if t not in clues and len(t) > 3:
                    clues.append(t)
            row["resolver_clues"] = clues[:20]
            row["version"] = VER
            merged_into += 1
            artifact_accepted.append(
                {
                    "cluster_id": c["cluster_id"],
                    "top_phrases": c["top_phrases"][:12],
                    "size": len(c["entries"]),
                    "mapped_to": best_id,
                    "action": "merged_into_existing",
                    "merge_jaccard": round(best_ov, 4),
                }
            )
            continue

        if len(new_concepts) >= MAX_NEW_CONCEPTS:
            skipped_cap += 1
            artifact_rejected.append(
                {
                    "cluster_id": c["cluster_id"],
                    "top_phrases": c["top_phrases"][:8],
                    "size": len(c["entries"]),
                    "frequency_sum": c["frequency_sum"],
                    "reason": f"max_new_concepts_cap_{MAX_NEW_CONCEPTS}",
                }
            )
            continue

        new_idx += 1
        cid = f"TFP_CLUSTER_{new_idx:03d}"
        parent = c.get("primary_parent")
        fam, area = pick_family_area(parent, index)
        top3 = c["top_phrases"][:3]
        plabel = _english_bundle_label(parent, index, new_idx)
        definition = (
            "RU: корпусный кластер формулировок, привязанный к родительскому TFP-понятию; "
            f"parent={parent or 'unknown'}. "
            f"Top phrases: {', '.join(top3)}."
        )
        parents_all = sorted(
            {resolve_corpus_concept_id(primary_cid(e), index) for e in c["entries"]} - {None}
        )
        related = [x for x in parents_all if x != cid][:12]
        lex_n = len(c["entries"])
        new_row: dict[str, Any] = {
            "concept_id": cid,
            "preferred_label": plabel[:200],
            "alt_labels": c["top_phrases"][:10],
            "definition": definition[:1200],
            "family_ids": fam,
            "area_ids": area,
            "specificity_rank": max(40, 75 - min(30, lex_n // 2)),
            "status": "active" if lex_n >= 3 else "draft",
            "version": VER,
            "related_concept_ids": related,
            "exclusion_concept_ids": [],
            "resolver_clues": sorted(t for t in sig if len(t) > 3)[:15],
            "hex_anchor": None,
        }
        index[cid] = new_row
        new_concepts.append(new_row)
        artifact_accepted.append(
            {
                "cluster_id": c["cluster_id"],
                "top_phrases": c["top_phrases"][:12],
                "size": len(c["entries"]),
                "mapped_to": cid,
                "action": "new_concept",
                "primary_parent": parent,
            }
        )

    rejected_clusters = generic_reject + skipped_empty + skipped_cap

    report: dict[str, Any] = {
        "existing_concepts": len(existing_rows),
        "new_candidates": len(valid),
        "accepted_new_concepts": len(new_concepts),
        "merged_into_existing": merged_into,
        "rejected_clusters": rejected_clusters,
        "_expansion_meta": {
            "clusters_built_pre_filter": len(clusters),
            "generic_reject": generic_reject,
            "skipped_empty_signature": skipped_empty,
            "skipped_cap": skipped_cap,
            "stripped_prior_TFP_CLUSTER_rows": stripped_clusters,
            "max_new_cap": MAX_NEW_CONCEPTS,
            "version": VER,
        },
        "_artifact_cluster_audit": {
            "accepted": artifact_accepted,
            "rejected": artifact_rejected,
            "rejected_pre_expand_truncated": len(rejected_pre_expand) >= MAX_REJECTED_CLUSTER_RECORDS,
        },
    }

    if not write:
        return report

    # Preserve stable order: existing rows in file order, then append new TFP_CLUSTER_* not in file
    existing_ids = {r["concept_id"] for r in existing_rows}
    out = []
    for r in existing_rows:
        cid = r["concept_id"]
        if cid in index:
            out.append(index[cid])
        else:
            out.append(r)
    for nc in new_concepts:
        if nc["concept_id"] not in existing_ids:
            out.append(nc)
    save_jsonl(DB_TFP, out)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    r = run(write=args.write)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if not args.write:
        print("\nDry run. Pass --write to rewrite dict_b_tfp.jsonl + report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
