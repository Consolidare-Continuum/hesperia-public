#!/usr/bin/env python3
"""
Build LEVEL 4 Dict-A lexical_markers.yaml from Dict-B concept_nodes.yaml.

Default: all operational areas A1–A10 (1440 nodes). Extracts Russian tokens from
label, example_context, definition; optional --corpus re-ranks tokens by corpus
frequency so markers match your texts.

Pilot mode (--pilot): only A2, A3, A4, A10 (legacy subset).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ONTOLOGY = REPO / "hesperia" / "ontology"
DICT_B_NODES = ONTOLOGY / "dictB" / "concept_nodes.yaml"
DICT_A_MARKERS = ONTOLOGY / "dictA" / "lexical_markers.yaml"

ALL_AREAS = frozenset(f"A{i}" for i in range(1, 11))
PILOT_AREAS = frozenset({"A2", "A3", "A4", "A10"})

# Слова, не используемые как маркеры (шум, местоимения, служебные)
RU_STOP = frozenset({
    "и", "в", "на", "с", "как", "что", "без", "для", "или", "при", "по", "из", "к", "о", "от", "до",
    "же", "бы", "ли", "не", "но", "а", "у", "за", "под", "над", "через", "между", "перед", "после",
    "когда", "если", "то", "это", "так", "уже", "ещё", "только", "даже", "всего", "всё", "более",
    "менее", "очень", "всегда", "иногда", "здесь", "там", "тогда", "теперь", "также", "например",
    "другой", "других", "собой", "себя", "него", "неё", "них", "чем", "который", "которая", "которые",
    "какой", "какая", "какие", "такой", "такая", "такие", "весь", "вся", "все", "свой", "своей",
    "наш", "ваш", "его", "её", "их", "мой", "твой", "пациент", "терапевт", "сессии",
})

MIN_LEN = 2
MAX_MARKERS_PER_SOURCE = 10
MIN_MARKERS_PER_CONCEPT = 5

# Дополнительные маркеры по областям (если из текста извлекли мало)
AREA_EXTRA_MARKERS: dict[str, list[str]] = {
    "A1": [
        "аффект", "влечение", "инстинкт", "либидо", "мотивация", "эмоция", "тревога",
        "страх", "депрессия", "аффективный", "биологический", "когнитивный",
    ],
    "A2": [
        "объект", "репрезентация", "идентичность", "отношения", "связь", "интеграция",
        "диффузия", "граница", "нарратив", "амбивалентность", "вина", "зависимость", "привязанность",
    ],
    "A3": [
        "защита", "проекция", "расщепление", "идеализация", "обесценивание", "диссоциация",
        "отрицание", "изоляция", "интроекция", "идентификация", "перенос", "контрперенос",
    ],
    "A4": [
        "агрессия", "ярость", "гнев", "ненависть", "враждебность", "презрение", "зависть",
        "вина", "репарация", "контроль", "доминирование", "садизм", "месть",
    ],
    "A5": [
        "эротизация", "агрессия", "сексуализация", "возбуждение", "фантазия", "импульс",
        "влечение", "либидо", "садизм", "мазохизм",
    ],
    "A6": [
        "грандиозность", "нарциссизм", "самооценка", "стыд", "зеркало", "идеализация",
        "обесценивание", "хрупкое", "язвимость",
    ],
    "A7": [
        "эмпатия", "сострадание", "понимание", "внимание", "отклик", "сопереживание",
        "альянс", "удержание", "контейнирование",
    ],
    "A8": [
        "реальность", "проверка", "восприятие", "суждение", "дисторсия", "психотическое",
        "объективный", "субъективный",
    ],
    "A9": [
        "перенос", "контрперенос", "интерпретация", "интернализация", "объект",
        "сопротивление", "инсайт",
    ],
    "A10": [
        "терапия", "лечение", "контракт", "сеттинг", "альянс", "интерпретация", "перенос",
        "сопротивление", "регрессия", "интеграция", "рамки", "границы", "сессия", "завершение",
    ],
}


def tokenize_ru(text: str) -> list[str]:
    """Извлечь русские слова (кириллица в токене)."""
    if not text or not isinstance(text, str):
        return []
    tokens = re.findall(r"[а-яёa-z\-']+", text.lower())
    return [
        t for t in tokens
        if len(t) >= MIN_LEN and t not in RU_STOP and re.search(r"[а-яё]", t)
    ]


def load_corpus_word_counts(corpus: Path, *, min_freq: int) -> Counter[str]:
    """Unigram counts over *.md under corpus (skips ``_*.md``)."""
    c: Counter[str] = Counter()
    if not corpus.is_dir():
        return c
    for md in sorted(corpus.rglob("*.md")):
        if md.name.startswith("_"):
            continue
        try:
            raw = md.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for w in re.findall(r"[а-яё]+", raw):
            if len(w) >= MIN_LEN and w not in RU_STOP:
                c[w] += 1
    return Counter({w: n for w, n in c.items() if n >= min_freq})


def extract_markers(
    *,
    label: str,
    definition: str,
    example_context: str,
    corpus_counter: Counter[str] | None,
) -> list[str]:
    """
    Label tokens first (deduped), then example + definition.
    If corpus_counter is set, remaining tail is sorted by corpus frequency (desc).
    """
    lab: list[str] = []
    seen: set[str] = set()
    for w in tokenize_ru(label):
        if w not in seen:
            seen.add(w)
            lab.append(w)

    rest: list[str] = []
    for w in tokenize_ru(example_context) + tokenize_ru(definition):
        if w not in seen:
            seen.add(w)
            rest.append(w)

    if corpus_counter:
        rest.sort(key=lambda w: (-corpus_counter.get(w, 0), -len(w)))

    merged = lab + rest
    return merged[:MAX_MARKERS_PER_SOURCE]


def build_entries(
    nodes: list[dict],
    *,
    areas: frozenset[str],
    corpus_counter: Counter[str] | None,
) -> tuple[list[dict], dict[str, int]]:
    entries: list[dict] = []
    concept_counts: dict[str, int] = {}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        area = node.get("area")
        if not nid or area not in areas:
            continue
        label = str(node.get("label") or "")
        definition = str(node.get("definition") or "")
        example_context = str(node.get("example_context") or "")
        markers = extract_markers(
            label=label,
            definition=definition,
            example_context=example_context,
            corpus_counter=corpus_counter,
        )
        extras = AREA_EXTRA_MARKERS.get(str(area), [])
        if len(markers) < MIN_MARKERS_PER_CONCEPT and extras:
            for extra in extras:
                if extra not in markers:
                    markers.append(extra)
                if len(markers) >= MIN_MARKERS_PER_CONCEPT:
                    break
        markers = markers[:MAX_MARKERS_PER_SOURCE]
        concept_counts[str(nid)] = len(markers)
        for m in markers:
            entries.append({
                "marker": m,
                "concept_id": str(nid),
                "language": "ru",
                "weight": 1.0,
            })

    return entries, concept_counts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build lexical_markers.yaml from concept_nodes.yaml")
    p.add_argument(
        "--pilot",
        action="store_true",
        help="Only areas A2, A3, A4, A10 (legacy pilot)",
    )
    p.add_argument(
        "--corpus",
        type=Path,
        default=None,
        help="Markdown tree: weight token choice by unigram frequency (min --corpus-min-freq)",
    )
    p.add_argument("--corpus-min-freq", type=int, default=3, help="Minimum corpus count for weighting")
    p.add_argument(
        "--output",
        type=Path,
        default=DICT_A_MARKERS,
        help="Destination YAML (default: hesperia/ontology/dictA/lexical_markers.yaml)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats only; do not write",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not DICT_B_NODES.exists():
        print(f"Dict-B nodes not found: {DICT_B_NODES}", file=sys.stderr)
        return 1

    with open(DICT_B_NODES, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = data.get("nodes") or []
    areas = PILOT_AREAS if args.pilot else ALL_AREAS

    corpus_counter: Counter[str] | None = None
    if args.corpus is not None:
        cpath = args.corpus.resolve()
        if not cpath.exists():
            print(f"Corpus path not found: {cpath}", file=sys.stderr)
            return 1
        full = load_corpus_word_counts(cpath, min_freq=1)
        corpus_counter = Counter({w: n for w, n in full.items() if n >= int(args.corpus_min_freq)})
        print(f"corpus: {cpath} → {len(corpus_counter)} types with freq>={args.corpus_min_freq}")

    entries, concept_counts = build_entries(nodes, areas=areas, corpus_counter=corpus_counter)

    desc = (
        "LEVEL 4 Dict-A: лексические маркеры для пилота A2, A3, A4, A10."
        if args.pilot
        else "LEVEL 4 Dict-A: лексические маркеры для всех областей A1–A10 (concept_nodes.yaml)."
    )
    if args.corpus is not None:
        desc += f" Corpus-weighted from {args.corpus}."

    out = {
        "version": 1,
        "domain": "TFP_KERNBERG",
        "language": "ru",
        "description": desc,
        "marker_count": len(entries),
        "concept_count": len(concept_counts),
        "entries": entries,
    }

    if args.dry_run:
        print(f"dry-run: would write {len(entries)} markers for {len(concept_counts)} concepts → {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        yaml.dump(out, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    total = len(entries)
    avg = total / len(concept_counts) if concept_counts else 0
    print(
        f"Written {total} marker entries for {len(concept_counts)} concepts "
        f"(avg {avg:.1f} per concept) to {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
