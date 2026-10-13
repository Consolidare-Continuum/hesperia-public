#!/usr/bin/env python3
# HESPERIA — RAD. CODEX TASK: BUILD__DICT_A_DICT_B_FROM_CORPUS__RU_TFP__V060
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Deterministic pipeline: corpus → RAW lexical archive (n-grams) → tagged → mapped →
promoted ACTIVE Dict A (core / variants / speech) + negatives + Dict B v060 seed +
_build_report.json.

RAW ≠ ACTIVE: ``dict_a/_raw/*`` is never loaded by ``run_dlcr_pipeline``.

Run:  python3 tools/build_ru_tfp_dictionary_stack.py --write
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "research" / "_noone_local" / "2_cleaned"
BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
CORPORA = BASE / "corpora"
RAW_DIR = BASE / "dict_a" / "_raw"
DICT_A = BASE / "dict_a"
DICT_B = BASE / "dict_b"
ANCHORS = BASE / "anchors" / "concept_hex_anchors_tfp.json"
VER_ACTIVE = "v0.6.0_ru_tfp_stack"
VER_RAW = "v0.6.0_raw_archive"

# --- Deterministic promotion thresholds (calibration levers) ---
FREQ_HIGH_UNIGRAM = 8
FREQ_HIGH_NGRAM = 4
CONF_CORE = 0.7
CONF_VARIANT = 0.5
MAX_CORE_TOKENS = 3
MIN_VARIANT_TOKENS = 3
# Raw archive: drop hapax n-grams (still in sentence JSONL); cap rows for repo size (deterministic sort).
MIN_RAW_FREQ = 2
MAX_RAW_ENTRIES = 300_000

TOKEN_RE = re.compile(r"[а-яёa-z0-9]+", re.I)

# Phase 4: canonical stack (9 concepts) — schema-safe family/area patterns
STACK_CONCEPTS: list[dict[str, Any]] = [
    {
        "concept_id": "TFP_IDENTITY_DIFFUSION",
        "preferred_label": "identity_diffusion",
        "alt_labels": ["диффузия идентичности", "не знаю кто я", "пустота идентичности"],
        "definition": "Нестабильность самоопределения и диффузность целей на пограничном уровне (Kernberg / TFP).",
        "family_ids": ["F4"],
        "area_ids": ["A2"],
        "specificity_rank": 80,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["идентичность", "пустота", "кто я"],
        "hex_anchor": "HX-2600",
    },
    {
        "concept_id": "TFP_OBJECT_RELATIONS",
        "preferred_label": "object_relations",
        "alt_labels": ["объектные отношения", "внутренние объекты", "репрезентации объекта"],
        "definition": "Внутренние представления значимых других и паттерны к ним отношения в структуре личности.",
        "family_ids": ["F7"],
        "area_ids": ["A2"],
        "specificity_rank": 75,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["объект", "отношения", "внутренний объект"],
        "hex_anchor": "HX-2601",
    },
    {
        "concept_id": "TFP_SPLITTING",
        "preferred_label": "splitting",
        "alt_labels": ["расщепление", "всё хорошо или всё плохо", "чёрно-белое мышление"],
        "definition": "Примитивная защита деления на идеализированно хорошее и презренно плохое без интеграции.",
        "family_ids": ["F5"],
        "area_ids": ["A3"],
        "specificity_rank": 85,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["хороший", "плохой", "идеализация"],
        "hex_anchor": "HX-2602",
    },
    {
        "concept_id": "TFP_DENIAL",
        "preferred_label": "denial",
        "alt_labels": ["отрицание", "не признаю", "как будто не было"],
        "definition": "Отрицание значимых аспектов реальности или аффективно заряженных фактов.",
        "family_ids": ["F8"],
        "area_ids": ["A3"],
        "specificity_rank": 78,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["отрицаю", "не верю", "не было"],
        "hex_anchor": "HX-2603",
    },
    {
        "concept_id": "TFP_PROJECTIVE_IDENTIFICATION",
        "preferred_label": "projective_identification",
        "alt_labels": ["проективная идентификация", "внушает мне чувство", "как будто я плохой"],
        "definition": "Выталкивание части самости в объект с давлением на восприятие другого.",
        "family_ids": ["F6"],
        "area_ids": ["A3"],
        "specificity_rank": 82,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["проекция", "внушает", "идентификация"],
        "hex_anchor": "HX-2604",
    },
    {
        "concept_id": "TFP_IDEALIZATION",
        "preferred_label": "idealization",
        "alt_labels": ["идеализация", "идеальный объект", "восхищение до крайности"],
        "definition": "Крайняя идеализация объекта как защита от переживания плохого объекта.",
        "family_ids": ["F9"],
        "area_ids": ["A3"],
        "specificity_rank": 79,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["идеал", "совершенн", "единственн"],
        "hex_anchor": "HX-2605",
    },
    {
        "concept_id": "TFP_DEVALUATION",
        "preferred_label": "devaluation",
        "alt_labels": ["обесценивание", "презрение", "ничтожество объекта"],
        "definition": "Резкое обесценивание после разочарования; защита от зависимости и стыда.",
        "family_ids": ["F10"],
        "area_ids": ["A3"],
        "specificity_rank": 79,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["презираю", "ничтожество", "мерзость"],
        "hex_anchor": "HX-2606",
    },
    {
        "concept_id": "TFP_POLARIZATION",
        "preferred_label": "polarization",
        "alt_labels": ["поляризация", "крайности", "колебания между полюсами"],
        "definition": "Колебание или фиксация между крайними полюсами переживания или оценки.",
        "family_ids": ["F11"],
        "area_ids": ["A3"],
        "specificity_rank": 70,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["крайность", "полюс", "колебан"],
        "hex_anchor": "HX-2607",
    },
    {
        "concept_id": "TFP_AFFECT_INSTABILITY",
        "preferred_label": "affect_instability",
        "alt_labels": ["аффективная нестабильность", "перепады настроения", "интенсивные аффекты"],
        "definition": "Быстрые интенсивные сдвиги аффекта характерные для пограничной организации.",
        "family_ids": ["F12"],
        "area_ids": ["A2"],
        "specificity_rank": 77,
        "status": "active",
        "version": VER_ACTIVE,
        "resolver_clues": ["аффект", "вспышка", "перепад"],
        "hex_anchor": "HX-2608",
    },
]

# Deterministic keyword roots for overlap scoring (normalized substring match)
CONCEPT_KEY_ROOTS: dict[str, tuple[str, ...]] = {
    "TFP_IDENTITY_DIFFUSION": ("идентичн", "кто я", "пустот", "диффуз", "я не знаю"),
    "TFP_OBJECT_RELATIONS": ("объектн", "объект ", " отношен", "репрезент"),
    "TFP_SPLITTING": ("расщепл", "хорош", "плох", "идеализ", "обесцен", "чёрно", "белое"),
    "TFP_DENIAL": ("отрицан", "не призна", "не было", "как будто не"),
    "TFP_PROJECTIVE_IDENTIFICATION": ("проектив", "внуша", "идентифик"),
    "TFP_IDEALIZATION": ("идеал", "восхищ", "совершен"),
    "TFP_DEVALUATION": ("обесцен", "презрен", "ничтожеств", "мерзост"),
    "TFP_POLARIZATION": ("поляриз", "крайност", "полюс", "колебан"),
    "TFP_AFFECT_INSTABILITY": ("аффект", "настроен", "вспышк", "интенсив"),
}

NEGATIVE_PHRASES: tuple[tuple[str, str], ...] = (
    ("расщепление атома", "TFP_SPLITTING"),
    ("проекция луча", "TFP_PROJECTIVE_IDENTIFICATION"),
    ("перенос данных", "TFP_PROJECTIVE_IDENTIFICATION"),
    ("отрицание доступа", "TFP_DENIAL"),
    ("объект программирования", "TFP_OBJECT_RELATIONS"),
    ("поляризация света", "TFP_POLARIZATION"),
)

SPEECH_MARKERS = ("я ", " я ", "мне ", " чувствую", "боюсь", "ненавижу", "люблю", "пусто", "один")


def nfkc_lower(s: str) -> str:
    t = unicodedata.normalize("NFKC", s)
    return t.lower()


def tokenize(s: str) -> list[str]:
    return TOKEN_RE.findall(nfkc_lower(s))


def normalize_phrase(s: str) -> str:
    toks = tokenize(s)
    return " ".join(toks) if toks else ""


def sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p.strip() for p in parts if p and len(p.strip()) > 10]


def ingest_corpus() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not SRC.is_dir():
        return rows
    for md in sorted(SRC.glob("*.md")):
        raw = md.read_text(encoding="utf-8", errors="replace")
        blob = nfkc_lower(raw)
        blob = re.sub(r"[ \t]+", " ", blob)
        for sent in sentence_split(blob):
            rows.append({"text": sent, "source": md.name})
    return rows


def extract_ngrams(sentence_rows: list[dict[str, str]]) -> tuple[Counter[str], dict[str, list[str]]]:
    freq: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for row in sentence_rows:
        text = row["text"]
        toks = tokenize(text)
        if len(toks) < 1:
            continue
        seen_local: set[str] = set()
        for n in range(1, 6):
            for i in range(0, len(toks) - n + 1):
                chunk = " ".join(toks[i : i + n])
                if not chunk or chunk in seen_local:
                    continue
                seen_local.add(chunk)
                freq[chunk] += 1
                if len(examples[chunk]) < 3:
                    examples[chunk].append(text[:240])
    return freq, dict(examples)


def _domain_roots_hit(nf: str) -> bool:
    for roots in CONCEPT_KEY_ROOTS.values():
        for root in roots:
            if root in nf:
                return True
    return False


def class_hint_for(nf: str, fr: int, n_tok: int) -> str:
    if fr >= FREQ_HIGH_UNIGRAM and n_tok == 1:
        return "candidate_core"
    if fr >= FREQ_HIGH_NGRAM and 2 <= n_tok <= MAX_CORE_TOKENS:
        return "candidate_core"
    if _domain_roots_hit(nf):
        if n_tok <= MAX_CORE_TOKENS:
            return "candidate_core"
        return "candidate_variant"
    if n_tok >= MIN_VARIANT_TOKENS:
        return "candidate_variant"
    padded = f" {nf} "
    if nf.startswith("я ") or " я " in padded or any(m in padded for m in SPEECH_MARKERS):
        return "candidate_speech"
    return "noise"


def map_confidence(nf: str) -> tuple[list[str], float]:
    hits: list[str] = []
    for cid, roots in CONCEPT_KEY_ROOTS.items():
        for r in roots:
            if r in nf:
                hits.append(cid)
                break
    if not hits:
        return [], 0.0
    # Deterministic: unique sorted, confidence = min(1.0, 0.35 + 0.15 * unique_roots_matched)
    uniq = sorted(set(hits))
    score = min(1.0, 0.35 + 0.2 * len(uniq))
    return uniq, round(score, 4)


def promote(
    mapped: list[dict[str, Any]],
) -> tuple[list[dict], list[dict], list[dict]]:
    core: list[dict] = []
    variants: list[dict] = []
    speech: list[dict] = []
    seen_nf: set[str] = set()
    ei_c = ei_v = ei_s = 0
    for row in mapped:
        nf = row["normalized_form"]
        if not nf or nf in seen_nf:
            continue
        ch = row.get("class_hint")
        fr = int(row.get("frequency") or 0)
        conf = float(row.get("confidence_hint") or 0)
        ntok = len(nf.split())
        cids = row.get("candidate_concept_ids") or []
        if not cids:
            continue
        base_entry = {
            "surface_form": row["surface_form"],
            "normalized_form": nf,
            "language": "ru",
            "candidate_concept_ids": cids[:3],
            "priority": min(100, 40 + min(fr, 30)),
            "version": VER_ACTIVE,
        }
        promoted = False
        if (
            ch == "candidate_core"
            and conf >= CONF_CORE
            and ntok <= MAX_CORE_TOKENS
            and (fr >= FREQ_HIGH_UNIGRAM or fr >= FREQ_HIGH_NGRAM or conf >= 0.85)
        ):
            ei_c += 1
            core.append(
                {
                    "entry_id": f"STACK_CORE_{ei_c:05d}",
                    "match_type": "phrase" if ntok > 1 else "exact",
                    **base_entry,
                }
            )
            promoted = True
        elif ch == "candidate_variant" and ntok >= MIN_VARIANT_TOKENS and conf >= CONF_VARIANT:
            ei_v += 1
            variants.append(
                {"entry_id": f"STACK_VAR_{ei_v:05d}", "match_type": "phrase", **base_entry}
            )
            promoted = True
        elif ch == "candidate_speech" or (
            conf >= 0.4
            and (
                nf.startswith("я ")
                or " я " in f" {nf} "
                or any(m.strip() in f" {nf} " for m in SPEECH_MARKERS if len(m.strip()) > 2)
            )
        ):
            ei_s += 1
            speech.append(
                {"entry_id": f"STACK_SP_{ei_s:05d}", "match_type": "pattern", **base_entry}
            )
            promoted = True
        if promoted:
            seen_nf.add(nf)
    return core, variants, speech


def augment_min_lexical(
    core: list[dict], variants: list[dict], speech: list[dict], minimum: int = 3
) -> list[dict]:
    """Deterministic fallback rows from canon alt_labels / resolver_clues (Phase 8 coverage)."""
    counts: Counter[str] = Counter()
    all_nf: set[str] = set()
    for layer in (core, variants, speech):
        for e in layer:
            all_nf.add(e["normalized_form"])
            for cid in e.get("candidate_concept_ids") or []:
                counts[cid] += 1
    extra: list[dict] = []
    n = 0
    for c in STACK_CONCEPTS:
        cid = c["concept_id"]
        while counts[cid] < minimum:
            n += 1
            label = None
            for cand in list(c.get("alt_labels") or []) + list(c.get("resolver_clues") or []):
                nn = normalize_phrase(cand)
                if nn and nn not in all_nf:
                    label = cand
                    all_nf.add(nn)
                    break
            if not label:
                break
            nn = normalize_phrase(label)
            extra.append(
                {
                    "entry_id": f"STACK_CANON_{n:04d}",
                    "surface_form": label,
                    "normalized_form": nn,
                    "language": "ru",
                    "match_type": "phrase" if len(nn.split()) > 1 else "exact",
                    "candidate_concept_ids": [cid],
                    "priority": 95,
                    "version": VER_ACTIVE,
                }
            )
            counts[cid] += 1
    return core + extra


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def merge_anchors(repo: Path, stack: list[dict[str, Any]]) -> None:
    p = repo / ANCHORS
    reg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    for c in stack:
        cid = c["concept_id"]
        ha = c.get("hex_anchor")
        if ha:
            reg[cid] = ha
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_pipeline(write: bool) -> dict[str, Any]:
    sentence_rows = ingest_corpus()
    freq, examples = extract_ngrams(sentence_rows)

    raw_items = [(nf, fr) for nf, fr in freq.items() if fr >= MIN_RAW_FREQ]
    raw_items.sort(key=lambda x: (-x[1], x[0]))
    truncated = len(raw_items) > MAX_RAW_ENTRIES
    raw_items = raw_items[:MAX_RAW_ENTRIES]
    raw_rows: list[dict[str, Any]] = []
    for idx, (nf, fr) in enumerate(raw_items, start=1):
        raw_rows.append(
            {
                "entry_id": f"RAW_{idx:06d}",
                "surface_form": nf,
                "normalized_form": nf,
                "frequency": fr,
                "examples": examples.get(nf, [])[:3],
                "status": "raw",
                "mapped": False,
            }
        )

    tagged: list[dict[str, Any]] = []
    for r in raw_rows:
        nf = r["normalized_form"]
        ntok = len(nf.split())
        fr = r["frequency"]
        tagged.append(
            {
                **r,
                "class_hint": class_hint_for(nf, fr, ntok),
            }
        )

    mapped: list[dict[str, Any]] = []
    for r in tagged:
        nf = r["normalized_form"]
        cids, conf = map_confidence(nf)
        mapped.append(
            {
                **r,
                "mapped": bool(cids),
                "candidate_concept_ids": cids,
                "confidence_hint": conf,
            }
        )

    core, variants, speech = promote(mapped)
    core = augment_min_lexical(core, variants, speech, minimum=3)
    negatives: list[dict[str, Any]] = []
    for i, (phrase, _cid) in enumerate(NEGATIVE_PHRASES, start=1):
        nfp = normalize_phrase(phrase)
        if not nfp:
            continue
        negatives.append(
            {
                "entry_id": f"STACK_NEG_{i:03d}",
                "surface_form": phrase,
                "normalized_form": nfp,
                "language": "ru",
                "match_type": "phrase" if " " in nfp else "exact",
                "candidate_concept_ids": [],
                "negative_patterns": ["*"],
                "priority": 999,
                "version": VER_ACTIVE,
            }
        )

    report = {
        "total_raw_entries": len(raw_rows),
        "raw_unique_ngrams_ge_min_freq": len([1 for _, f in freq.items() if f >= MIN_RAW_FREQ]),
        "raw_truncated": truncated,
        "raw_max_entries": MAX_RAW_ENTRIES,
        "min_raw_frequency": MIN_RAW_FREQ,
        "core_entries": len(core),
        "variant_entries": len(variants),
        "speech_entries": len(speech),
        "negative_entries": len(negatives),
        "concept_count": len(STACK_CONCEPTS),
        "sentences_ingested": len(sentence_rows),
        "version": VER_ACTIVE,
    }

    if not write:
        return report

    CORPORA.mkdir(parents=True, exist_ok=True)
    write_jsonl(CORPORA / "tfp_ru_sentences.jsonl", sentence_rows)
    write_jsonl(RAW_DIR / "dict_a_ru_full_corpus.jsonl", raw_rows)
    write_jsonl(RAW_DIR / "dict_a_ru_full_tagged.jsonl", tagged)
    write_jsonl(RAW_DIR / "dict_a_ru_mapped.jsonl", mapped)
    write_jsonl(DICT_A / "dict_a_tfp_ru_core.jsonl", core)
    write_jsonl(DICT_A / "dict_a_tfp_ru_variants.jsonl", variants)
    write_jsonl(DICT_A / "dict_a_tfp_ru_speech.jsonl", speech)
    write_jsonl(DICT_A / "dict_a_tfp_ru_negative.jsonl", negatives)
    write_jsonl(DICT_B / "dict_b_tfp_ru_v060.jsonl", STACK_CONCEPTS)
    (BASE / "_build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    merge_anchors(REPO, STACK_CONCEPTS)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    r = run_pipeline(write=args.write)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if not args.write:
        print("\nDry run. Pass --write to emit files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
