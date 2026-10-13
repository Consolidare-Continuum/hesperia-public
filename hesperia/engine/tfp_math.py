"""Engine-owned TFP math primitives used by calculus."""

from __future__ import annotations

import math
import re
from typing import Any

from core.math.entropy_metrics import compute_entropy as _entropy

TFP_STAGES = (
    "chaotic",
    "defense_clarification",
    "interpretation",
    "integration",
)


def detect_tfp_stage(areas: dict[str, float], families: dict[str, float] | None = None) -> str:
    areas = areas or {}
    a2 = float(areas.get("A2", 0.0))
    a3 = float(areas.get("A3", 0.0))
    a4 = float(areas.get("A4", 0.0))
    a7 = float(areas.get("A7", 0.0))
    if a4 >= 0.5 and a3 >= 0.4 and a7 < 0.3:
        return "chaotic"
    if a3 >= 0.45 and a4 >= 0.2:
        return "defense_clarification"
    if a7 >= 0.5 and a4 < 0.4:
        return "integration"
    if a2 >= 0.2 or a3 >= 0.2:
        return "interpretation"
    return "chaotic"


def stage_from_timeline(timeline: list[dict[str, Any]], last_n: int = 1) -> str:
    if not timeline or last_n < 1:
        return "chaotic"
    slice_ = timeline[-last_n:]
    areas_agg: dict[str, float] = {}
    for step in slice_:
        for k, v in (step.get("areas") or {}).items():
            areas_agg[k] = areas_agg.get(k, 0.0) + float(v)
    n = len(slice_)
    if n > 0:
        areas_agg = {k: v / n for k, v in areas_agg.items()}
    return detect_tfp_stage(areas_agg)


LOW_INTENSITY = re.compile(r"\b(недоволен|раздражен|грустно|обижен|злюсь|злиться)\b", re.IGNORECASE)
MEDIUM_INTENSITY = re.compile(r"\b(злость|ярость|ненависть|в ярости|очень злюсь|сильно обижен)\b", re.IGNORECASE)
HIGH_INTENSITY = re.compile(r"\b(в бешенстве|ненавижу|убить готов|разрывает|бесит|капец|жесть|достал)\b", re.IGNORECASE)
EXCLAMATION = re.compile(r"[!?]{1,3}\s*$")
MULTIPLE_EXCLAMATION = re.compile(r"!{2,}")


def estimate_affect_intensity(text: str, tokens: list[str] | None = None) -> float:
    if not text or not isinstance(text, str):
        return 0.0
    text_lower = text.strip().lower()
    score = 0.0
    if HIGH_INTENSITY.search(text_lower):
        score = max(score, 0.85)
    if MEDIUM_INTENSITY.search(text_lower):
        score = max(score, 0.55)
    if LOW_INTENSITY.search(text_lower):
        score = max(score, 0.35)
    if MULTIPLE_EXCLAMATION.search(text):
        score = min(1.0, score + 0.15)
    elif EXCLAMATION.search(text.strip()):
        score = min(1.0, score + 0.08)
    if score == 0.0 and (tokens or []):
        affect_tokens = {"зло", "злой", "злиться", "ненависть", "агрессия", "злюсь", "бешусь"}
        norm = [t.lower() for t in (tokens or [])]
        if any(t in affect_tokens for t in norm):
            score = 0.25
    return round(min(1.0, max(0.0, score)), 2)


def compute_confidence_scores(activation: dict[str, Any]) -> dict[str, Any]:
    areas = activation.get("areas") or {}
    families = activation.get("families") or {}
    concepts = activation.get("concepts") or {}

    def level_confidence(d: dict[str, float]) -> float:
        if not d:
            return 0.0
        vals = [float(v) for v in d.values()]
        m = max(vals) if vals else 0.0
        ent = _entropy(vals)
        max_ent = math.log2(len(vals)) if len(vals) > 1 else 1.0
        norm_ent = ent / max_ent if max_ent > 0 else 0
        return round(min(1.0, m * (1.0 - norm_ent * 0.5)), 2)

    dom_area = max(areas, key=lambda k: areas[k]) if areas else ""
    dom_family = max(families, key=lambda k: families[k]) if families else ""
    return {
        "areas": {k: round(float(v), 2) for k, v in areas.items()},
        "families": {k: round(float(v), 2) for k, v in families.items()},
        "concepts": {k: round(float(v), 2) for k, v in concepts.items()},
        "dominant_area_confidence": round(float(areas.get(dom_area, 0.0)), 2),
        "dominant_family_confidence": round(float(families.get(dom_family, 0.0)), 2),
        "area_level_confidence": level_confidence(areas),
        "family_level_confidence": level_confidence(families),
    }


CLARIFICATION_PATTERNS = [
    r"\b(что вы имеете в виду|что вы чувствуете|что происходит|расскажите подробнее|как это было|уточните)\b",
    r"\b(what do you mean|what are you feeling|can you say more|tell me more|how was that)\b",
]
CONFRONTATION_PATTERNS = [
    r"\b(заметил противоречие|с одной стороны.*с другой|вы только что сказали|но ранее вы)\b",
    r"\b(I notice a contradiction|on one hand.*on the other|you just said|but earlier you)\b",
]
INTERPRETATION_PATTERNS = [
    r"\b(возможно вы|похоже что|как если бы|это может означать|интерпретируя)\b",
    r"\b(perhaps you|it seems that|as if|this might mean|interpreting)\b",
]
LIMIT_SETTING_PATTERNS = [
    r"\b(нельзя|нужно остановиться|граница|правило|должен прервать)\b",
    r"\b(we need to stop|boundary|rule|I have to interrupt|cannot allow)\b",
]
SUPPORT_PATTERNS = [
    r"\b(понимаю|слышу вас|это трудно|принимаю|поддерживаю)\b",
    r"\b(I understand|I hear you|that is hard|I accept|support)\b",
]


def classify_intervention(text: str) -> str:
    if not text or not isinstance(text, str):
        return "support"
    text_lower = text.lower().strip()
    patterns = {
        "clarification": [re.compile(p, re.IGNORECASE) for p in CLARIFICATION_PATTERNS],
        "confrontation": [re.compile(p, re.IGNORECASE) for p in CONFRONTATION_PATTERNS],
        "interpretation": [re.compile(p, re.IGNORECASE) for p in INTERPRETATION_PATTERNS],
        "limit_setting": [re.compile(p, re.IGNORECASE) for p in LIMIT_SETTING_PATTERNS],
        "support": [re.compile(p, re.IGNORECASE) for p in SUPPORT_PATTERNS],
    }
    for label in ("confrontation", "limit_setting", "interpretation", "clarification", "support"):
        for pat in patterns[label]:
            if pat.search(text_lower):
                return label
    return "support"


def detect_interaction_loops(
    timeline: list[dict[str, Any]],
    therapist_utterances: list[tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    if not timeline or len(timeline) < 2:
        return []
    loops: list[dict[str, Any]] = []
    for i in range(1, len(timeline)):
        prev, curr = timeline[i - 1], timeline[i]
        areas_prev = prev.get("areas") or {}
        fam_prev = prev.get("families") or {}
        accusation = float(areas_prev.get("A4", 0.0)) >= 0.3 or float(fam_prev.get("A2_F3", 0.0)) >= 0.3
        p = float((prev.get("areas") or {}).get("A4", 0.0))
        c = float((curr.get("areas") or {}).get("A4", 0.0))
        escalation = c > p and (c - p) >= 0.15
        intervention_type = "unknown"
        if therapist_utterances:
            for idx, text in therapist_utterances:
                if idx == i:
                    intervention_type = classify_intervention(text)
                    break
        if accusation and escalation:
            loops.append(
                {
                    "window_index": i,
                    "accusation": True,
                    "intervention_type": intervention_type,
                    "escalation": True,
                    "projective_identification_signal": intervention_type == "clarification",
                }
            )
    return loops

