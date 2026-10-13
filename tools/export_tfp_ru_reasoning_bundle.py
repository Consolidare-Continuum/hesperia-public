#!/usr/bin/env python3
"""Export a Russian, LLM-friendly "reasoning bundle" for a TFP session output directory.

Writes 3 artifacts (per session_id):
  - 13_<session>_iterations_ru.jsonl
  - 13_<session>_annotated_transcript_ru.md
  - 13_<session>_roadmap_ru.json

Grounding sources:
  - DLCR: 04_dlcr_full.json → canonical_text + span_resolutions (with char offsets)
  - Topology: 09_session_topology.json → state_sequence/defense_timeline/area_curves (aggression_curve compat) (patient turns)
  - Dict A/B (RU): assets/data/engine_dynamics_v060/dict_a + dict_b
  - TRIZ/KME: 12_* and 07_session_kme.json (optional)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO = Path(__file__).resolve().parents[1]

DICT_A_TFP_RU = REPO / "assets" / "data" / "engine_dynamics_v060" / "dict_a" / "dict_a_tfp_ru_aligned.jsonl"
DICT_B_TFP = REPO / "assets" / "data" / "engine_dynamics_v060" / "dict_b" / "dict_b_tfp.jsonl"
CONCEPT_NODES_YAML = REPO / "hesperia" / "ontology" / "dictB" / "concept_nodes.yaml"

# Human-facing RU names grounded in existing clinical report layer.
sys.path.insert(0, str(REPO))
try:
    from research.clinical_tfp.interpretation import DEFENSE_MAP
    from research.clinical_tfp.report_generator import AREA_NAMES_RU, DEFENSE_NAMES_RU
except Exception:
    # Minimal fallback: keep the exporter usable even if package imports are unavailable.
    AREA_NAMES_RU = {
        "A1": "влечения и аффекты",
        "A2": "объектные отношения",
        "A3": "защитные операции",
        "A4": "агрессия",
        "A5": "перверсии",
        "A6": "нарциссизм",
        "A7": "любовь / реляционная способность",
        "A8": "структурный диагноз",
        "A9": "терапевтическая техника",
        "A10": "процесс лечения",
        "A11": "интеграция / сублимация",
        "A12": "взаимное признание / анти-грандиозность",
    }
    DEFENSE_MAP = {
        "A3_F1": "splitting",
        "A3_F2": "idealization_devaluation",
        "A3_F3": "dissociation",
        "A3_F4": "projection",
        "A3_F5": "projective_identification",
        "A3_F6": "role_reversal",
    }
    DEFENSE_NAMES_RU = {
        "splitting": "расщепление",
        "idealization_devaluation": "идеализация и обесценивание",
        "dissociation": "диссоциация",
        "projection": "проекция",
        "projective_identification": "проективная идентификация",
        "role_reversal": "реверс ролей",
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


@dataclass(frozen=True)
class TurnSpan:
    turn_index: int
    speaker: str  # patient / therapist / client (normalized)
    speaker_raw: str
    header_start: int
    content_start: int
    content_end: int
    text: str


SPEAKER_RE = re.compile(r"(?i)\b(пациент|терапевт|аналитик|клиент)\s*:\s*")


def _norm_speaker_ru(s: str) -> str:
    s = s.strip().lower()
    if s == "пациент":
        return "patient"
    if s in {"терапевт", "аналитик"}:
        return "therapist"
    if s == "клиент":
        return "client"
    return s


def _speaker_ru_label(speaker: str) -> str:
    if speaker == "patient":
        return "пациент"
    if speaker == "therapist":
        return "терапевт"
    if speaker == "client":
        return "клиент"
    return speaker


def parse_turns_ru(canonical_text: str) -> list[TurnSpan]:
    matches = list(SPEAKER_RE.finditer(canonical_text))
    if not matches:
        return []

    turns: list[TurnSpan] = []
    for i, m in enumerate(matches):
        header_start = m.start()
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(canonical_text)
        speaker_raw = m.group(1)
        speaker = _norm_speaker_ru(speaker_raw)
        text = canonical_text[content_start:content_end].strip()
        turns.append(
            TurnSpan(
                turn_index=i,
                speaker=speaker,
                speaker_raw=speaker_raw,
                header_start=header_start,
                content_start=content_start,
                content_end=content_end,
                text=text,
            )
        )
    return turns


_A_STATE_RE = re.compile(r"^A([1-9]|10)$")
_A3_FAMILY_RE = re.compile(r"^A3_F[0-9]+$")


def _area_name_ru(area_id: str | None) -> str | None:
    if not isinstance(area_id, str) or not area_id:
        return None
    return AREA_NAMES_RU.get(area_id, None)


def _defense_marker_ru(marker: Any) -> str | None:
    """
    Translate a topology "defense marker" into Russian, without leaking internal IDs.

    Marker formats observed in topology outputs:
      - role_reversal (pattern name)
      - A3_F6 (family id for defense patterns)
      - other A3_F* codes (may be out-of-map) → return None
    """
    if not isinstance(marker, str) or not marker:
        return None
    if marker in DEFENSE_NAMES_RU:
        return DEFENSE_NAMES_RU.get(marker)
    if _A3_FAMILY_RE.match(marker):
        pattern = DEFENSE_MAP.get(marker)
        if pattern:
            return DEFENSE_NAMES_RU.get(pattern) or pattern
    return None


def load_dict_a_entry_by_id(path: Path = DICT_A_TFP_RU) -> dict[str, dict[str, Any]]:
    rows = _read_jsonl(path)
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows:
        eid = r.get("entry_id")
        if isinstance(eid, str) and eid:
            by_id[eid] = r
    return by_id


def load_dict_b_tfp_by_concept_id(path: Path = DICT_B_TFP) -> dict[str, dict[str, Any]]:
    rows = _read_jsonl(path)
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows:
        cid = r.get("concept_id")
        if isinstance(cid, str) and cid:
            by_id[cid] = r
    return by_id


def load_concept_nodes_by_id(path: Path = CONCEPT_NODES_YAML) -> dict[str, dict[str, Any]]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in doc:
        if not isinstance(row, dict):
            continue
        cid = row.get("id")
        if isinstance(cid, str) and cid:
            out[cid] = row
    return out


def _concept_info_ru(
    concept_id: str,
    dict_b_tfp: dict[str, dict[str, Any]],
    concept_nodes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if concept_id in dict_b_tfp:
        r = dict_b_tfp[concept_id]
        alt = r.get("alt_labels") or []
        return {
            "concept_id": concept_id,
            "метка": (alt[0] if alt else None) or r.get("preferred_label") or concept_id,
            "альтернативы": alt,
            "определение": r.get("definition") or "",
            "area_ids": r.get("area_ids") or [],
            "family_ids": r.get("family_ids") or [],
            "hex_anchor": r.get("hex_anchor"),
            "источник": "dict_b_tfp.jsonl",
        }

    if concept_id in concept_nodes:
        r = concept_nodes[concept_id]
        return {
            "concept_id": concept_id,
            "метка": r.get("label") or concept_id,
            "альтернативы": [],
            "определение": r.get("definition") or "",
            "area_ids": [r.get("area")] if r.get("area") else [],
            "family_ids": [r.get("family")] if r.get("family") else [],
            "hex_anchor": None,
            "источник": "concept_nodes.yaml",
        }

    return {
        "concept_id": concept_id,
        "метка": concept_id,
        "альтернативы": [],
        "определение": "",
        "area_ids": [],
        "family_ids": [],
        "hex_anchor": None,
        "источник": "unknown",
    }


def _stable_round(x: Any, ndigits: int = 6) -> Any:
    if isinstance(x, float):
        return round(x, ndigits)
    return x


def _as_pct_0_1(x: Any) -> float | None:
    if not isinstance(x, (int, float)):
        return None
    return round(float(x) * 100.0, 1)


def _pct_of_max(x: Any, max_value: Any) -> float | None:
    if not isinstance(x, (int, float)) or not isinstance(max_value, (int, float)):
        return None
    mv = float(max_value)
    if mv <= 0.0:
        return None
    return round(float(x) * 100.0 / mv, 1)


def _sum_scores(items: Iterable[tuple[str, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in items:
        out[k] = out.get(k, 0.0) + float(v)
    return out


def build_turn_records_ru(
    *,
    session_id: str,
    turns: list[TurnSpan],
    span_resolutions: list[dict[str, Any]],
    topology: dict[str, Any] | None,
    dict_a_by_entry: dict[str, dict[str, Any]],
    dict_b_tfp: dict[str, dict[str, Any]],
    concept_nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    patient_turns = [t for t in turns if t.speaker == "patient"]
    patient_idx_by_turn_index: dict[int, int] = {t.turn_index: i for i, t in enumerate(patient_turns)}

    topo = topology or {}
    state_sequence: list[str] = list(topo.get("state_sequence") or [])
    defense_timeline: list[Any] = list(topo.get("defense_timeline") or [])
    if isinstance(topo.get("aggression_curve"), list):
        aggression_curve: list[Any] = list(topo["aggression_curve"])
    else:
        aggression_curve = list((topo.get("area_curves") or {}).get("aggression") or [])
    segments_agg: list[dict[str, Any]] = list(topo.get("segments") or [])

    n_patient_topology = (
        min(len(patient_turns), len(state_sequence), len(defense_timeline), len(aggression_curve)) if state_sequence else 0
    )

    records: list[dict[str, Any]] = []
    for t in turns:
        spans = [
            s
            for s in span_resolutions
            if isinstance(s.get("source_char_start"), int)
            and isinstance(s.get("source_char_end"), int)
            and t.content_start <= int(s["source_char_start"]) < t.content_end
        ]

        evidence: list[dict[str, Any]] = []
        scored_concepts: list[tuple[str, float]] = []
        for s in spans:
            winning = s.get("winning_concept_id")
            if not isinstance(winning, str) or not winning:
                continue
            entry_ids = [x for x in (s.get("lexical_entry_ids") or []) if isinstance(x, str)]
            entry_row = dict_a_by_entry.get(entry_ids[0]) if entry_ids else None

            cand_scores = s.get("candidate_scores") or {}
            score = cand_scores.get(winning) if isinstance(cand_scores, dict) else None
            if isinstance(score, (int, float)):
                scored_concepts.append((winning, float(score)))

            evidence.append(
                {
                    "фрагмент": s.get("source_text_span"),
                    "символы": {"start": s.get("source_char_start"), "end": s.get("source_char_end")},
                    "lexical_entry_ids": entry_ids,
                    "словарь_A": {
                        "surface_form": (entry_row or {}).get("surface_form"),
                        "normalized_form": (entry_row or {}).get("normalized_form"),
                        "match_type": (entry_row or {}).get("match_type"),
                        "priority": (entry_row or {}).get("priority"),
                        "version": (entry_row or {}).get("version"),
                    }
                    if entry_row
                    else None,
                    "кандидаты": s.get("candidate_concepts") or [],
                    "оценки": cand_scores,
                    "победитель": _concept_info_ru(winning, dict_b_tfp, concept_nodes),
                    "причины": s.get("winning_reason_codes") or [],
                }
            )

        concept_score_sum = _sum_scores(scored_concepts)
        top_concepts_scored = sorted(concept_score_sum.items(), key=lambda kv: kv[1], reverse=True)[:12]
        top_concept_max = top_concepts_scored[0][1] if top_concepts_scored else None

        families_score_sum: dict[str, float] = {}
        areas_score_sum: dict[str, float] = {}
        for cid, sc in concept_score_sum.items():
            info = _concept_info_ru(cid, dict_b_tfp, concept_nodes)
            for a in info.get("area_ids") or []:
                areas_score_sum[a] = areas_score_sum.get(a, 0.0) + float(sc)
            for f in info.get("family_ids") or []:
                families_score_sum[f] = families_score_sum.get(f, 0.0) + float(sc)

        top_areas = sorted(areas_score_sum.items(), key=lambda kv: kv[1], reverse=True)[:8]
        top_families = sorted(families_score_sum.items(), key=lambda kv: kv[1], reverse=True)[:12]

        # Attach Hesperia topology for patient turns (and carry-forward for therapist turns).
        patient_i = patient_idx_by_turn_index.get(t.turn_index)
        topo_for_turn: dict[str, Any] | None = None
        dynamics: dict[str, Any] | None = None
        if patient_i is not None and patient_i < n_patient_topology:
            prev_state = state_sequence[patient_i - 1] if patient_i > 0 else None
            curr_state = state_sequence[patient_i]
            prev_aggr = aggression_curve[patient_i - 1] if patient_i > 0 and patient_i - 1 < len(aggression_curve) else None
            curr_aggr = aggression_curve[patient_i] if patient_i < len(aggression_curve) else None
            d_aggr = (float(curr_aggr) - float(prev_aggr)) if isinstance(curr_aggr, (int, float)) and isinstance(prev_aggr, (int, float)) else None
            marker_raw = defense_timeline[patient_i] if patient_i < len(defense_timeline) else None
            dynamics = {
                "область_до": prev_state,
                "область_после": curr_state,
                "область_до_ru": _area_name_ru(prev_state),
                "область_после_ru": _area_name_ru(curr_state),
                "смена_области": bool(prev_state and curr_state and prev_state != curr_state),
                "агрессия": _stable_round(float(curr_aggr), 4) if isinstance(curr_aggr, (int, float)) else None,
                "агрессия_до": _stable_round(float(prev_aggr), 4) if isinstance(prev_aggr, (int, float)) else None,
                "агрессия_delta": _stable_round(float(d_aggr), 4) if isinstance(d_aggr, (int, float)) else None,
                "защитный_маркер_ru": _defense_marker_ru(marker_raw),
            }
            topo_for_turn = {
                "индекс_пациента": patient_i,
                "состояние": curr_state,
                "переход": {"из": prev_state, "в": curr_state},
                "агрессия": _stable_round(aggression_curve[patient_i], 4) if patient_i < len(aggression_curve) else None,
                "маркер_защиты": defense_timeline[patient_i] if patient_i < len(defense_timeline) else None,
                "сегмент_агрегированный": segments_agg[patient_i] if patient_i < len(segments_agg) else None,
                "источник": "topology:patient",
            }
        elif patient_i is None and state_sequence:
            prev_patients = [pi for ti, pi in patient_idx_by_turn_index.items() if ti < t.turn_index]
            carry = max(prev_patients) if prev_patients else None
            if carry is not None and carry < n_patient_topology:
                prev_state = state_sequence[carry - 1] if carry > 0 else None
                curr_state = state_sequence[carry]
                marker_raw = defense_timeline[carry] if carry < len(defense_timeline) else None
                curr_aggr = aggression_curve[carry] if carry < len(aggression_curve) else None
                dynamics = {
                    "область_до": prev_state,
                    "область_после": curr_state,
                    "область_до_ru": _area_name_ru(prev_state),
                    "область_после_ru": _area_name_ru(curr_state),
                    "смена_области": bool(prev_state and curr_state and prev_state != curr_state),
                    "агрессия": _stable_round(float(curr_aggr), 4) if isinstance(curr_aggr, (int, float)) else None,
                    "агрессия_до": None,
                    "агрессия_delta": None,
                    "защитный_маркер_ru": _defense_marker_ru(marker_raw),
                }
                topo_for_turn = {
                    "индекс_пациента": carry,
                    "состояние": curr_state,
                    "переход": {"из": prev_state, "в": curr_state},
                    "агрессия": _stable_round(aggression_curve[carry], 4) if carry < len(aggression_curve) else None,
                    "маркер_защиты": defense_timeline[carry] if carry < len(defense_timeline) else None,
                    "сегмент_агрегированный": segments_agg[carry] if carry < len(segments_agg) else None,
                    "источник": "topology:carried_from_patient",
                }

        analysis_lines: list[str] = []
        if topo_for_turn and isinstance(topo_for_turn.get("переход"), dict):
            p = topo_for_turn["переход"]
            if p.get("из") and p.get("в"):
                if p["из"] != p["в"]:
                    analysis_lines.append(f"Переход состояния: {p['из']} → {p['в']}.")
                else:
                    analysis_lines.append(f"Состояние без смены: {p['в']}.")
            elif p.get("в"):
                analysis_lines.append(f"Начальное состояние: {p['в']}.")

        if top_concepts_scored:
            labels: list[str] = []
            for cid, sc in top_concepts_scored[:6]:
                info = _concept_info_ru(cid, dict_b_tfp, concept_nodes)
                labels.append(f"{info.get('метка')} ({cid})≈{_stable_round(sc, 2)}")
            analysis_lines.append("Ключевые концепты (по DLCR): " + "; ".join(labels) + ".")

        if topo_for_turn and topo_for_turn.get("маркер_защиты"):
            analysis_lines.append(f"Маркер защиты/сдвига: {topo_for_turn['маркер_защиты']}.")

        records.append(
            {
                "сессия_id": session_id,
                "итерация_id": f"{session_id}:{t.turn_index:03d}",
                "порядок": t.turn_index,
                "говорящий": _speaker_ru_label(t.speaker),
                "текст": t.text,
                "границы_в_тексте": {"start": t.content_start, "end": t.content_end},
                "топология": topo_for_turn,
                "динамика": dynamics,
                "доказательства_DLCR": evidence,
                "агрегации": {
                    "топ_концепты": [
                        {
                            "score_sum": _stable_round(sc, 4),
                            "score_pct_of_top": _pct_of_max(sc, top_concept_max) if top_concept_max is not None else None,
                            **_concept_info_ru(cid, dict_b_tfp, concept_nodes),
                        }
                        for cid, sc in top_concepts_scored
                    ],
                    "топ_области": [{"area_id": a, "score_sum": _stable_round(sc, 4)} for a, sc in top_areas],
                    "топ_семейства": [{"family_id": f, "score_sum": _stable_round(sc, 4)} for f, sc in top_families],
                },
                "анализ_ru": " ".join(analysis_lines).strip(),
            }
        )

    return records


def build_markdown_ru(
    *,
    session_id: str,
    records: list[dict[str, Any]],
    meta: dict[str, Any],
    audience: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Сессия {session_id} — аннотированная расшифровка")
    if meta:
        lines.append("\n## Метаданные")
        # Keep only person-friendly metadata (no coordinates, no internal IDs).
        if "turns_total" in meta:
            lines.append(f"- Всего реплик: {meta['turns_total']}")
        if "turns_patient" in meta:
            lines.append(f"- Реплик пациента: {meta['turns_patient']}")
        if "turns_therapist" in meta:
            lines.append(f"- Реплик терапевта: {meta['turns_therapist']}")
    lines.append("\n## Итерации (по очереди в тексте)\n")
    for r in records:
        lines.append(f"### {r['порядок']:03d}. {r['говорящий'].capitalize()}\n")
        txt = (r.get("текст") or "").strip()
        lines.append(txt if txt else "(пусто)")

        dyn = r.get("динамика") or {}
        if dyn:
            lines.append("\n**Динамика:**")
            before = dyn.get("область_до_ru")
            after = dyn.get("область_после_ru")
            if before and after:
                if dyn.get("смена_области"):
                    lines.append(f"- Смена ведущей области: {before} → {after}")
                else:
                    lines.append(f"- Ведущая область без смены: {after}")
            elif after:
                lines.append(f"- Ведущая область: {after}")

            ag = dyn.get("агрессия")
            if ag is not None:
                delta = dyn.get("агрессия_delta")
                ag_pct = _as_pct_0_1(ag)
                delta_pct = _as_pct_0_1(delta) if isinstance(delta, (int, float)) else None
                if ag_pct is not None and delta_pct is not None:
                    sign = "+" if delta_pct > 0 else ""
                    lines.append(f"- Интенсивность (агрессия): {ag_pct}% (Δ {sign}{delta_pct} п.п.)")
                elif ag_pct is not None:
                    lines.append(f"- Интенсивность (агрессия): {ag_pct}%")
                else:
                    lines.append(f"- Интенсивность (агрессия): {ag}")

            defense_ru = dyn.get("защитный_маркер_ru")
            if defense_ru:
                lines.append(f"- Защитный манёвр: {defense_ru}")

        ag = r.get("агрегации") or {}
        topc = ag.get("топ_концепты") or []
        if topc:
            lines.append("\n**Ключевые темы (по текстовым маркерам):**")
            for c in topc[:10]:
                label = c.get("метка") or c.get("concept_id")
                # Do not print internal IDs; keep Russian label + approximate weight.
                pct = c.get("score_pct_of_top")
                if isinstance(pct, (int, float)):
                    lines.append(f"- {label} (выраженность≈{pct}%)")
                else:
                    lines.append(f"- {label}")

        ev = r.get("доказательства_DLCR") or []
        if ev:
            lines.append("\n**Фрагменты текста, на которых основаны темы:**")
            for e in ev[:12]:
                frag = e.get("фрагмент")
                win = (e.get("победитель") or {})
                wlabel = win.get("метка") or win.get("concept_id")
                lines.append(f'- "{frag}" → {wlabel}')

            if audience == "specialist":
                lines.append("\n**Триггеры (сработавшие маркеры словаря/правила):**")
                for e in ev[:12]:
                    frag = e.get("фрагмент")
                    dct = e.get("словарь_A") or {}
                    marker = dct.get("surface_form")
                    norm = dct.get("normalized_form")
                    mtype = dct.get("match_type")
                    pr = dct.get("priority")
                    reasons = e.get("причины") or []
                    win = (e.get("победитель") or {})
                    wlabel = win.get("метка") or win.get("concept_id")
                    parts = [f'фрагмент="{frag}"', f'тема="{wlabel}"']
                    if marker:
                        parts.append(f'маркер="{marker}"')
                    if norm and norm != marker:
                        parts.append(f'норма="{norm}"')
                    if mtype:
                        parts.append(f"тип={mtype}")
                    if pr is not None:
                        parts.append(f"prio={pr}")
                    if reasons:
                        parts.append("reasons=" + ",".join(str(x) for x in reasons[:6]))
                    lines.append("- " + "; ".join(parts))

        lines.append("\n---\n")
    return "\n".join(lines).strip() + "\n"


def build_roadmap_ru(
    *,
    session_id: str,
    manifest: dict[str, Any],
    dlcr_session: dict[str, Any] | None,
    sealed_session: dict[str, Any] | None,
    topology: dict[str, Any] | None,
    stages: dict[str, Any] | None,
    triz_metrics: dict[str, Any] | None,
    triz_dynamics: dict[str, Any] | None,
    cross_plane_audit: dict[str, Any] | None,
    contradiction_hotspots: dict[str, Any] | None,
    kme: dict[str, Any] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "сессия_id": session_id,
        "описание": "Дорожная карта: состояния/переходы + TRIZ/KME сигналы (на русском).",
        "manifest": {
            "run": manifest.get("run"),
            "run_id": manifest.get("run_id"),
            "dlcr_mode": (manifest.get("flags") or {}).get("dlcr_mode"),
            "domain_pack": (manifest.get("flags") or {}).get("HESPERIA_DLCR_DOMAIN_PACK"),
        },
    }

    if stages:
        ss = (stages.get("session_tfp_stages") or [])
        for row in ss:
            if row.get("session_id") == session_id:
                out["tfp_stage"] = row.get("tfp_stage")
                out["areas_top"] = row.get("areas_top")
                if isinstance(row.get("areas_top"), dict):
                    out["areas_top_ru"] = {AREA_NAMES_RU.get(a, a): _stable_round(v, 4) for a, v in row["areas_top"].items()}
                break

    if topology:
        out["топология"] = {
            "segments_total": topology.get("_segments_total"),
            "segments_truncated": topology.get("_segments_truncated"),
            "state_sequence": topology.get("state_sequence"),
            "transitions": topology.get("transitions"),
            "defense_timeline": topology.get("defense_timeline"),
            "area_curves": topology.get("area_curves"),
            "aggression_curve": topology.get("aggression_curve"),
            "curve_projection_meta": topology.get("curve_projection_meta"),
        }

        seq = list(topology.get("state_sequence") or [])
        borders: list[dict[str, Any]] = []
        for i in range(1, len(seq)):
            if seq[i] != seq[i - 1]:
                borders.append({"индекс": i, "из": seq[i - 1], "в": seq[i]})
        out["границы_состояний"] = borders

        if seq:
            unique_states = sorted(set(seq))
            out["сводка_потока"] = {
                "уникальные_состояния": unique_states,
                "уникальные_состояния_ru": [AREA_NAMES_RU.get(a, a) for a in unique_states],
                "переходов": len(topology.get("transitions") or []),
                "границ": len(borders),
            }

    if triz_metrics:
        out["triz"] = triz_metrics
    if triz_dynamics:
        out["triz_dynamics"] = triz_dynamics
        dyn_pct: dict[str, float] = {}
        for k, v in (triz_dynamics or {}).items():
            if isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0:
                dyn_pct[k] = _as_pct_0_1(v) or 0.0
        if dyn_pct:
            out["triz_dynamics_pct"] = dyn_pct
    if cross_plane_audit:
        out["cross_plane_audit"] = cross_plane_audit
        if isinstance(cross_plane_audit.get("topology_activation"), (int, float)):
            out["cross_plane_audit_pct"] = {"topology_activation": _as_pct_0_1(cross_plane_audit["topology_activation"])}
    if contradiction_hotspots:
        out["contradiction_hotspots"] = contradiction_hotspots.get("hotspots") or contradiction_hotspots

    if kme:
        sess = (kme.get("sessions") or [None])[0]
        rep = (sess or {}).get("report") or {}
        out["kme_triz"] = rep.get("triz")

    collateral: dict[str, Any] = {}
    if dlcr_session:
        geom = dlcr_session.get("segment_hex_geometry") or {}
        l1_drifts = geom.get("l1_drifts") if isinstance(geom, dict) else None
        persistence = geom.get("persistence_scores") if isinstance(geom, dict) else None
        drift_vals = [float(x) for x in l1_drifts] if isinstance(l1_drifts, list) and all(isinstance(x, (int, float)) for x in l1_drifts) else []
        pers_vals = [float(x) for x in persistence] if isinstance(persistence, list) and all(isinstance(x, (int, float)) for x in persistence) else []
        drift_events = sum(1 for x in drift_vals if x > 0)
        drift_rate = (drift_events / len(drift_vals)) if drift_vals else None
        mean_pers = (sum(pers_vals) / len(pers_vals)) if pers_vals else None
        collateral["dlcr"] = {
            "lexical_hits_accepted": dlcr_session.get("lexical_hits_accepted"),
            "lexical_hits_rejected": dlcr_session.get("lexical_hits_rejected"),
            "degradation_flags": dlcr_session.get("degradation_flags") or [],
            "hex_concentration": dlcr_session.get("hex_concentration"),
            "hex_dispersion": dlcr_session.get("hex_dispersion"),
            "segment_trajectory": dlcr_session.get("segment_trajectory"),
            "segment_hex_geometry_summary": {
                "segments": len(drift_vals) or None,
                "drift_events": drift_events or 0,
                "drift_event_rate_pct": _as_pct_0_1(drift_rate) if isinstance(drift_rate, (int, float)) else None,
                "mean_persistence_pct": _as_pct_0_1(mean_pers) if isinstance(mean_pers, (int, float)) else None,
            }
            if drift_vals or pers_vals
            else None,
        }
    if sealed_session:
        sig = sealed_session.get("product_signals") or {}
        numeric = {k: float(v) for k, v in sig.items() if isinstance(v, (int, float))}
        mx = max(numeric.values()) if numeric else None
        collateral["sealed"] = {
            "hspr_index": sealed_session.get("hspr_index"),
            "innovation_index": sealed_session.get("innovation_index"),
            "narrative_density": sealed_session.get("narrative_density"),
            "propagation_strength": sealed_session.get("propagation_strength"),
            "contradiction_pressure": sealed_session.get("contradiction_pressure"),
            "hex_energy_mode": sealed_session.get("hex_energy_mode"),
            "product_signals_raw": sig,
            "product_signals_pct_of_max": {k: _pct_of_max(v, mx) for k, v in numeric.items()} if mx else {},
        }
    if collateral:
        out["доп_показатели"] = collateral

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-dir", required=True, help="Output bundle dir, e.g. hesperia/outputs/tfp_full_...")
    ap.add_argument("--out-dir", default=None, help="Where to write results (default: bundle dir)")
    ap.add_argument("--session-id", default=None, help="Restrict to a single session_id")
    ap.add_argument("--audience", default="human", choices=["human", "specialist"], help="Markdown audience: human or specialist")
    ap.add_argument("--write", action="store_true", help="Write artifacts")
    args = ap.parse_args()

    bundle_dir = Path(args.bundle_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else bundle_dir

    manifest = _read_json(bundle_dir / "00_manifest.json")
    session_ids = list(manifest.get("session_ids") or [])
    if args.session_id:
        session_ids = [args.session_id]

    dlcr = _read_json(bundle_dir / "04_dlcr_full.json")
    sealed_full = _read_json(bundle_dir / "05_sealed_multiscale.json") if (bundle_dir / "05_sealed_multiscale.json").exists() else None
    topo_full = _read_json(bundle_dir / "09_session_topology.json")
    stages = _read_json(bundle_dir / "02_session_tfp_stages.json") if (bundle_dir / "02_session_tfp_stages.json").exists() else None

    dict_a_by_entry = load_dict_a_entry_by_id()
    dict_b_tfp = load_dict_b_tfp_by_concept_id()
    concept_nodes = load_concept_nodes_by_id()

    dlcr_sessions = {s.get("session_id"): s for s in (dlcr.get("sessions") or []) if isinstance(s, dict)}
    topo_sessions = {s.get("session_id"): s for s in (topo_full.get("sessions") or []) if isinstance(s, dict)}
    sealed_sessions = (
        {s.get("session_id"): s for s in ((sealed_full or {}).get("sessions") or []) if isinstance(s, dict)} if sealed_full else {}
    )

    all_written: list[Path] = []
    for sid in session_ids:
        s = dlcr_sessions.get(sid)
        if not s:
            raise SystemExit(f"No DLCR session found for session_id={sid}")

        canonical_text = s.get("canonical_text")
        if not isinstance(canonical_text, str) or not canonical_text.strip():
            raise SystemExit(f"Missing canonical_text for session_id={sid}")

        turns = parse_turns_ru(canonical_text)
        span_resolutions = list(s.get("span_resolutions") or [])
        topo = (topo_sessions.get(sid) or {}).get("session_topology")

        records = build_turn_records_ru(
            session_id=sid,
            turns=turns,
            span_resolutions=span_resolutions,
            topology=topo,
            dict_a_by_entry=dict_a_by_entry,
            dict_b_tfp=dict_b_tfp,
            concept_nodes=concept_nodes,
        )

        # Optional TRIZ/KME files can be per-session; load lazily.
        triz_metrics_path = bundle_dir / f"12_{sid}_triz_metrics_v1.json"
        triz_dyn_path = bundle_dir / f"12_{sid}_triz_dynamics.json"
        xplane_path = bundle_dir / f"12_{sid}_cross_plane_audit.json"
        hotspots_path = bundle_dir / f"12_{sid}_contradiction_hotspots.json"
        triz_metrics = _read_json(triz_metrics_path) if triz_metrics_path.exists() else None
        triz_dynamics = _read_json(triz_dyn_path) if triz_dyn_path.exists() else None
        cross_plane_audit = _read_json(xplane_path) if xplane_path.exists() else None
        hotspots = _read_json(hotspots_path) if hotspots_path.exists() else None
        kme = _read_json(bundle_dir / "07_session_kme.json") if (bundle_dir / "07_session_kme.json").exists() else None
        sealed_session = sealed_sessions.get(sid) if sealed_sessions else None

        meta = {
            "bundle_dir": str(bundle_dir),
            "dlcr_mode": s.get("mode"),
            "turns_total": len(turns),
            "turns_patient": sum(1 for t in turns if t.speaker == "patient"),
            "turns_therapist": sum(1 for t in turns if t.speaker == "therapist"),
            "span_resolutions": len(span_resolutions),
        }
        md = build_markdown_ru(session_id=sid, records=records, meta=meta, audience=args.audience)
        roadmap = build_roadmap_ru(
            session_id=sid,
            manifest=manifest,
            dlcr_session=s,
            sealed_session=sealed_session,
            topology=topo,
            stages=stages,
            triz_metrics=triz_metrics,
            triz_dynamics=triz_dynamics,
            cross_plane_audit=cross_plane_audit,
            contradiction_hotspots=hotspots,
            kme=kme,
        )

        if args.write:
            out_dir.mkdir(parents=True, exist_ok=True)
            jsonl_path = out_dir / f"13_{sid}_iterations_ru.jsonl"
            md_path = out_dir / f"13_{sid}_annotated_transcript_ru.md"
            roadmap_path = out_dir / f"13_{sid}_roadmap_ru.json"
            jsonl_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
            md_path.write_text(md, encoding="utf-8")
            roadmap_path.write_text(json.dumps(roadmap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            all_written.extend([jsonl_path, md_path, roadmap_path])
        else:
            print(json.dumps({"session_id": sid, "records": len(records)}, ensure_ascii=False))

    if args.write:
        print("written:")
        for p in all_written:
            print(str(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
