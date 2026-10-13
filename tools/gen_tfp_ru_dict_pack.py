#!/usr/bin/env python3
# HESPERIA — RAD. Generate Russian TFP DLCR starter pack (Ethan TASK 1 seed).
# DEPRECATED for operator builds: use ``tools/build_ru_tfp_dictionary_stack.py`` (Codex stack).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Emit dict_a RU layers, append Dict B TFP_* rows, extend concept_hex_anchors_tfp.json.

Run from repo root: python3 tools/gen_tfp_ru_dict_pack.py --write

Targets in ETHAN doc: expand toward 100–300 core / 200–500 variants via corpus pass.
This commit lands a validated **starter** (~32 concepts, 3+ lexical hooks each).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "assets" / "data" / "engine_dynamics_v060"
VER = "v0.6.0_ru_tfp"

# (concept_id, preferred_label_en, definition_ru, area_id, family_id, resolver_clues_ru, core_phrase_ru)
# family/area: schema patterns ^A([1-9]|10)$, ^F[0-9]+$
CONCEPTS: list[tuple[str, str, str, str, str, list[str], str]] = [
    ("TFP_SPLITTING", "splitting", "Примитивная защита: деление переживаний и объектов на крайности «всё хорошо» / «всё плохо» без интеграции амбивалентности.", "A3", "F5", ["хороший", "плохой", "идеализация", "обесценивание"], "расщепление как защита"),
    ("TFP_PROJECTIVE_IDENTIFICATION", "projective identification", "Механизм, при котором часть самости выталкивается в объект; контроль и слияние с объектом через проекцию.", "A3", "F6", ["внушает", "заставляет чувствовать", "как будто я"], "проективная идентификация"),
    ("TFP_INTROJECTION", "introjection", "Внутреннее поглощение качеств объекта без дифференциации; ранние формы идентификации.", "A3", "F7", ["внутри меня", "становлюсь как"], "интроекция"),
    ("TFP_DENIAL", "denial", "Отрицание восприятия реальности, эмоционально заряженных фактов или значимых аспектов ситуации.", "A3", "F8", ["не было", "это неправда", "не признаю"], "отрицание"),
    ("TFP_PRIMITIVE_IDEALIZATION", "primitive idealization", "Крайняя идеализация объекта как защита от переживания плохого объекта.", "A3", "F9", ["идеальный", "единственный спаситель"], "примитивная идеализация"),
    ("TFP_PRIMITIVE_DEVALUATION", "primitive devaluation", "Резкое обесценивание после разочарования; защита от зависимости и стыда.", "A3", "F10", ["ничтожество", "мерзость", "презрение"], "обесценивание объекта"),
    ("TFP_OMNIPOTENT_CONTROL", "omnipotent control", "Фантазия тотального контроля объекта или ситуации как защита от беспомощности.", "A3", "F11", ["контролирую", "должен слушаться"], "всемогущий контроль"),
    ("TFP_WITHDRAWAL", "withdrawal", "Изоляция аффекта и сужение контакта; защита через отстранение.", "A3", "F12", ["отстраняюсь", "не чувствую", "пустота"], "изоляция аффекта"),
    ("TFP_DISSOCIATION", "dissociation", "Расщепление переживания, памяти или идентичности под стрессом.", "A3", "F13", ["как во сне", "не помню", "отрезвело"], "диссоциация"),
    ("TFP_IDENTITY_DIFFUSION", "identity diffusion", "Нестабильность самоопределения, диффузность целей и ценностей при пограничном уровне.", "A2", "F4", ["не знаю кто я", "пустота внутри"], "диффузия идентичности"),
    ("TFP_NEGATIVE_THERAPEUTIC_REACTION", "negative therapeutic reaction", "Ухудшение при прогрессе терапии из-за зависти, вины или разрушения хорошего объекта.", "A10", "F8", ["стало хуже после прогресса", "разрушаю помощь"], "негативная терапевтическая реакция"),
    ("TFP_ENVY", "envy", "Разрушительное желание лишить другого хорошего из-за собственной пустоты.", "A3", "F14", ["завидую", "не могу вынести что у него"], "зависть"),
    ("TFP_PRIMITIVE_ENVY", "primitive envy", "Ранняя форма зависти с орально-разрушительным окрасом.", "A3", "F15", ["съесть", "уничтожить хорошее"], "примитивная зависть"),
    ("TFP_PRIMITIVE_GRATITUDE", "primitive gratitude", "Нестабильная благодарность, быстро сменяющаяся обесцениванием.", "A3", "F16", ["благодарен", "но потом ненавижу"], "примитивная благодарность"),
    ("TFP_ENVIOUS_TAKING", "envious taking", "Присвоение хорошего у другого через завистливую атаку.", "A3", "F17", ["отбираю", "не дам ему"], "завистливое присвоение"),
    ("TFP_MALIGNANT_NARCISSISM", "malignant narcissism", "Сочетание нарциссизма, антисоциальных черт, парааноидности и садизма.", "A4", "F18", ["месть", "унижение", "контроль через страх"], "злокачественный нарциссизм"),
    ("TFP_NARCISSISTIC_PERSONALITY", "narcissistic personality organization", "Нарциссическая структура личности с грандiosity и хрупким самоуважением.", "A4", "F19", ["уникальность", "унижение если не восхищаются"], "нарциссическая организация личности"),
    ("TFP_BORDERLINE_PERSONALITY", "borderline personality organization", "Пограничная организация: расщепление, идентичностная диффузия, примитивная защита.", "A2", "F8", ["перенос", "интенсивность", "импульсивность"], "пограничная организация личности"),
    ("TFP_ANTISOCIAL_FEATURES", "antisocial features", "Манипуляции, нарушение правил, агрессивное использование других.", "A5", "F3", ["обман", "нарушаю правила"], "антисоциальные черты"),
    ("TFP_PARANOID_FEATURES", "paranoid features", "Подозрительность, идеи референции, проекция угрозы.", "A6", "F7", ["преследуют", "все против меня"], "параноидные черты"),
    ("TFP_TRANSFERENCE", "transference", "Перенос ранних объектных отношений на терапевта в здесь-и-сейчас.", "A10", "F5", ["перенос", "как с родителем"], "перенос"),
    ("TFP_COUNTERTRANSFERENCE", "countertransference", "Реакции терапевта, отражающие проекции пациента и собственные зоны напряжения.", "A10", "F6", ["контрперенос", "терапевт реагирует"], "контрперенос"),
    ("TFP_THERAPEUTIC_ALLIANCE", "therapeutic alliance", "Рабочий союз для исследования переноса и сопротивления.", "A10", "F10", ["альянс", "сотрудничество"], "терапевтический альянс"),
    ("TFP_WORKING_THROUGH", "working through", "Повторяющаяся проработка конфликтов после озарений.", "A10", "F12", ["проработка", "снова возвращаемся"], "проработка"),
    ("TFP_SPLITTING_OFF_AGGRESSION", "splitting off aggression", "Отделение агрессии и её выселение во внешний объект.", "A3", "F4", ["агрессия наружу", "виноват он"], "выселение агрессии"),
    ("TFP_SEXUALIZATION", "sexualization", "Сексуализация конфликта или отношений как защита от зависимости или стыда.", "A7", "F9", ["эротизация", "секс вместо близости"], "сексуализация"),
    ("TFP_IMPULSE_RAGE", "impulsive rage", "Вспышки ярости при угрозе самости или объекту.", "A5", "F11", ["ярость", "не сдержался", "разбил"], "импульсивная ярость"),
    ("TFP_AFFECTIVE_STORMS", "affective storms", "Интенсивные аффективные разряды при пограничной организации.", "A2", "F12", ["аффективный шторм", "не выношу интенсивность"], "аффективные бури"),
    ("TFP_REPRESENTATION_SELF", "self representation", "Внутреннее представление себя в объектных отношениях.", "A2", "F6", ["образ себя", "как я себя вижу"], "репрезентация себя"),
    ("TFP_REPRESENTATION_OBJECT", "object representation", "Внутреннее представление значимого другого.", "A2", "F7", ["образ другого", "как я его вижу"], "объектная репрезентация"),
    ("TFP_PARTIAL_DRIVE_DERIVATIVE", "partial drive derivative", "Частично-влечениевые производные в структуре характера.", "A8", "F5", ["оральное", "анальное", "фиксация"], "частично-влечениевые производные"),
    ("TFP_SUPEREGO_INTEGRATION", "superego integration", "Интеграция суперэго и способность к вине и ценностям без разрушения.", "A9", "F8", ["вина", "совесть", "мораль"], "интеграция суперэго"),
    ("TFP_ORAL_DEPENDENCY", "oral dependency", "Зависимость, связанная с оральной фазой и страхом потери объекта.", "A7", "F4", ["нужен другой", "боюсь остаться один"], "оральная зависимость"),
]

NEGATIVES: list[tuple[str, str, str]] = [
    ("A_RU_NEG_001", "расщепление атома", "physical/chemistry sense blocks clinical splitting"),
    ("A_RU_NEG_002", "проекция луча", "optical projection"),
    ("A_RU_NEG_003", "перенос данных", "IT sense"),
    ("A_RU_NEG_004", "трансфер футболиста", "sports transfer"),
    ("A_RU_NEG_005", "идеал газового закона", "physics ideal gas"),
    ("A_RU_NEG_006", "контроль версий", "software VCS"),
    ("A_RU_NEG_007", "альянс стран", "political alliance"),
    ("A_RU_NEG_008", "зависть к успеху стартапа", "colloquial noise — block long phrase only if curated"),
    ("A_RU_NEG_009", "отрицание доступа", "IT access denied"),
    ("A_RU_NEG_010", "пограничное значение функции", "math boundary"),
    ("A_RU_NEG_011", "объект программирования", "CS object"),
    ("A_RU_NEG_012", "нарциссизм инфлюенсера", "pop culture — optional block phrase"),
]


def _norm(s: str) -> str:
    return s.strip().lower()


def build_dict_b_rows(hex_start: int = 2500) -> tuple[list[dict[str, Any]], dict[str, str]]:
    rows: list[dict[str, Any]] = []
    anchors: dict[str, str] = {}
    hx = hex_start
    for cid, label, def_ru, area, fam, clues, core_ru in CONCEPTS:
        hx_id = f"HX-{hx:04d}"
        hx += 1
        alts = [core_ru] + [c for c in clues[:4] if c]
        rows.append(
            {
                "concept_id": cid,
                "preferred_label": label,
                "alt_labels": alts,
                "definition": def_ru,
                "family_ids": [fam],
                "area_ids": [area],
                "specificity_rank": 72,
                "status": "active",
                "version": VER,
                "resolver_clues": clues,
                "hex_anchor": hx_id,
            }
        )
        anchors[cid] = hx_id
    return rows, anchors


def build_dict_a_layers() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    core: list[dict] = []
    variants: list[dict] = []
    speech: list[dict] = []
    neg: list[dict] = []
    n = 0
    for cid, _label, _def, _a, _f, clues, phrase in CONCEPTS:
        n += 1
        sf = phrase
        nf = _norm(sf)
        core.append(
            {
                "entry_id": f"A_RU_{n:04d}",
                "surface_form": sf,
                "normalized_form": nf,
                "language": "ru",
                "match_type": "phrase",
                "candidate_concept_ids": [cid],
                "priority": 100,
                "version": VER,
            }
        )
        # variants: alternate wording + clue phrases
        variants.append(
            {
                "entry_id": f"A_RU_{1000 + n:04d}",
                "surface_form": clues[0] if clues else sf,
                "normalized_form": _norm(clues[0]) if clues else nf,
                "language": "ru",
                "match_type": "phrase" if " " in (clues[0] if clues else "") else "exact",
                "candidate_concept_ids": [cid],
                "priority": 80,
                "version": VER,
            }
        )
        if len(clues) > 1:
            variants.append(
                {
                    "entry_id": f"A_RU_{2000 + n:04d}",
                    "surface_form": clues[1],
                    "normalized_form": _norm(clues[1]),
                    "language": "ru",
                    "match_type": "exact",
                    "candidate_concept_ids": [cid],
                    "priority": 75,
                    "version": VER,
                }
            )
        # speech / pattern layer
        speech.append(
            {
                "entry_id": f"A_RU_{3000 + n:04d}",
                "surface_form": f"чувствую что связано с {clues[0] if clues else 'этим'}",
                "normalized_form": _norm(f"чувствую что связано с {clues[0] if clues else 'этим'}"),
                "language": "ru",
                "match_type": "pattern",
                "candidate_concept_ids": [cid],
                "priority": 60,
                "version": VER,
            }
        )
    for eid, phrase, _note in NEGATIVES:
        neg.append(
            {
                "entry_id": eid,
                "surface_form": phrase,
                "normalized_form": _norm(phrase),
                "language": "ru",
                "match_type": "phrase" if " " in phrase else "exact",
                "candidate_concept_ids": [],
                "negative_patterns": ["*"],
                "priority": 999,
                "version": VER,
            }
        )
    return core, variants, speech, neg


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write files under assets/data/engine_dynamics_v060")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    core, variants, speech, neg = build_dict_a_layers()
    db_rows, new_anchors = build_dict_b_rows()
    print(
        f"core={len(core)} variants={len(variants)} speech={len(speech)} neg={len(neg)} dict_b_new={len(db_rows)}"
    )
    if not args.write:
        print("Dry run only. Pass --write to emit files.")
        return 0
    da = BASE / "dict_a"
    write_jsonl(da / "dict_a_tfp_ru_core.jsonl", core)
    write_jsonl(da / "dict_a_tfp_ru_variants.jsonl", variants)
    write_jsonl(da / "dict_a_tfp_ru_speech.jsonl", speech)
    write_jsonl(da / "dict_a_tfp_ru_negative.jsonl", neg)
    print(f"Wrote dict_a RU layers under {da}")
    db_path = BASE / "dict_b" / "dict_b_tfp.jsonl"
    existing = [json.loads(l) for l in db_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    have = {r["concept_id"] for r in existing}
    appended = 0
    with db_path.open("a", encoding="utf-8") as f:
        for r in db_rows:
            if r["concept_id"] in have:
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            appended += 1
    print(f"Appended {appended} Dict B rows to {db_path}")
    anch_path = BASE / "anchors" / "concept_hex_anchors_tfp.json"
    reg = json.loads(anch_path.read_text(encoding="utf-8"))
    reg.update(new_anchors)
    anch_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated anchors in {anch_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
