# HESPERIA — LEVEL 5/6 Session text → concept activation pipeline
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
TEXT → CONCEPT pipeline: tokenize → normalize → (tokens + ngrams) → detect markers → activate concepts.
Aggregates to concept_score, family_score, area_score. Output: semantic activation map.

LEVEL 7 (Session topology) использует этот вывод для структурной интерпретации:
dominant defenses, dominant object relations, aggression intensity, relational capacity;
dominant_area, dominant_family, secondary_area и т.д.
"""

from __future__ import annotations

import math
import re
from typing import Any

from hesperia.nlp.invariant_activation import build_invariant_activation

# RU negation lemmas → dampen token/phrase triggers in a short window (clinical heuristic).
_NEGATION_TOKENS = frozenset({"не", "нет", "ни"})

# Lazy imports for ontology (optional paths for tests)
def _get_marker_index():
    from hesperia.ontology.dictA import build_marker_to_concepts
    return build_marker_to_concepts()

def _get_phrase_index():
    from hesperia.ontology.dictA import build_phrase_marker_index
    return build_phrase_marker_index()

def _get_concept_to_af():
    from hesperia.ontology.dictB import build_concept_to_area_family
    return build_concept_to_area_family()


def _get_merged_marker_index() -> dict[str, list[tuple[str, float]]]:
    """Lexical + colloquial markers for enhanced Russian activation (token/lemma weight 1.0, colloquial 1.2)."""
    from hesperia.ontology.dictA import build_marker_to_concepts, build_colloquial_marker_index
    main = build_marker_to_concepts()
    coll = build_colloquial_marker_index()
    out = dict(main)
    for k, v in coll.items():
        out.setdefault(k, []).extend(v)
    return out


def tokenize_text(text: str) -> list[str]:
    """
    Разбить текст на токены (слова). Сохраняются буквы (кириллица, латиница), цифры, дефис.
    """
    if not text or not isinstance(text, str):
        return []
    # Одна или более букв/цифр/дефиса подряд
    return re.findall(r"[а-яёa-z0-9\-]+", text, re.IGNORECASE)


def normalize_tokens(tokens: list[str]) -> list[str]:
    """Нормализовать токены: нижний регистр, обрезка пробелов."""
    return [t.strip().lower() for t in tokens if isinstance(t, str) and t.strip()]


def build_ngrams(tokens: list[str], n: int = 2) -> list[str]:
    """
    Построить n-граммы из токенов (перекрывающиеся окна). Возвращает список строк "w1 w2 ... wn".
    """
    if not tokens or n < 1 or n > len(tokens):
        return []
    out: list[str] = []
    for i in range(len(tokens) - n + 1):
        ngram = " ".join(tokens[i : i + n])
        out.append(ngram)
    return out


def negation_weight_factor(
    tokens: list[str],
    anchor_index: int,
    window: int = 2,
    multiplier: float = 0.5,
) -> float:
    """
    If a negation token appears within ``window`` of ``anchor_index``, scale weight by ``multiplier``.
    Default multiplier 0.5 = dampen (not invert polarity — minimal scope).
    """
    if not tokens or multiplier >= 1.0:
        return 1.0
    lo = max(0, int(anchor_index) - int(window))
    hi = min(len(tokens), int(anchor_index) + int(window) + 1)
    for j in range(lo, hi):
        if tokens[j] in _NEGATION_TOKENS:
            return float(multiplier)
    return 1.0


def build_ngram_tuples(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    """
    Построить n-граммы как кортежи токенов для O(1) lookup в phrase_index.
    Возвращает [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)].
    """
    if not tokens or n < 1 or n > len(tokens):
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def detect_markers(
    tokens: list[str],
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    *,
    apply_negation: bool = False,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
) -> list[tuple[str, float]]:
    """
    Для каждого токена найти совпадения в marker_index. Возвращает список (concept_id, weight).
    marker_index: нормализованный маркер → [(concept_id, weight), ...].
    """
    index = marker_index if marker_index is not None else _get_marker_index()
    out: list[tuple[str, float]] = []
    for i, t in enumerate(tokens):
        hits = index.get(t)
        if not hits:
            continue
        fac = (
            negation_weight_factor(tokens, i, negation_window, negation_multiplier)
            if apply_negation
            else 1.0
        )
        for cid, w in hits:
            out.append((cid, float(w) * fac))
    return out


def detect_phrase_markers(
    ngrams: list[str] | None = None,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    tokens: list[str] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    *,
    apply_negation: bool = False,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
) -> list[tuple[str, float]]:
    """
    Фразовые маркеры: (1) по ngrams+marker_index (строки) или (2) по tokens+phrase_index (кортежи, O(n)).

    Вариант 1: ngrams — список строк "w1 w2", marker_index — маркер → [(concept_id, weight)].
    Вариант 2: tokens — нормализованные токены, phrase_index — build_phrase_marker_index();
    строит биграммы и триграммы, lookup по кортежам, возвращает совпадения.
    """
    if tokens is not None and phrase_index is not None:
        out: list[tuple[str, float]] = []
        for n in (2, 3):
            key = f"phrase_length_{n}"
            idx = phrase_index.get(key) or {}
            if len(tokens) < n:
                continue
            for i in range(len(tokens) - n + 1):
                tup = tuple(tokens[i : i + n])
                hits = idx.get(tup)
                if not hits:
                    continue
                anchor = i + n - 1
                fac = (
                    negation_weight_factor(tokens, anchor, negation_window, negation_multiplier)
                    if apply_negation
                    else 1.0
                )
                for cid, w in hits:
                    out.append((cid, float(w) * fac))
        return out
    # Legacy: string ngrams + marker_index
    if ngrams is None:
        return []
    index = marker_index if marker_index is not None else _get_marker_index()
    out = []
    for phrase in ngrams:
        hits = index.get(phrase)
        if hits:
            out.extend(hits)
    return out


def activate_concepts(
    markers: list[tuple[str, float]],
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    normalize_scores: bool = True,
    *,
    per_concept_score_cap: float | None = None,
    use_log1p_concept_scores: bool = False,
) -> dict[str, Any]:
    """
    Агрегировать маркеры в оценки по концептам, семьям и областям.

    - concept_score = Σ marker_weight по каждому concept_id
    - family_score = Σ concept_scores для концептов в этой семье (ключ "A3_F6")
    - area_score = Σ family_scores для семей в этой области

    Если normalize_scores=True, каждый уровень масштабируется так, что максимум = 1.0.

    Опционально: ``per_concept_score_cap`` — потолок суммы весов на концепт (длинные сегменты);
    ``use_log1p_concept_scores`` — сжатие вклада ``log(1 + sum)`` (альтернатива cap).
    """
    af = concept_to_area_family if concept_to_area_family is not None else _get_concept_to_af()

    # concept_id → сумма весов
    concept_scores: dict[str, float] = {}
    for cid, w in markers:
        concept_scores[cid] = concept_scores.get(cid, 0.0) + w

    if use_log1p_concept_scores:
        concept_scores = {k: math.log1p(max(0.0, v)) for k, v in concept_scores.items()}
    elif per_concept_score_cap is not None:
        cap = float(per_concept_score_cap)
        concept_scores = {k: min(float(v), cap) for k, v in concept_scores.items()}

    # family: "A3_F6" → сумма concept_scores
    family_scores: dict[str, float] = {}
    for cid, score in concept_scores.items():
        if cid not in af:
            continue
        area, family = af[cid]
        key = f"{area}_{family}"
        family_scores[key] = family_scores.get(key, 0.0) + score

    # area → сумма family_scores
    area_scores: dict[str, float] = {}
    for fkey, score in family_scores.items():
        area = fkey.split("_")[0] if "_" in fkey else fkey
        area_scores[area] = area_scores.get(area, 0.0) + score

    def _norm(d: dict[str, float]) -> dict[str, float]:
        if not d or not normalize_scores:
            return d
        m = max(d.values())
        if m <= 0:
            return d
        return {k: round(v / m, 2) for k, v in d.items()}

    return {
        "concepts": _norm(concept_scores),
        "families": _norm(family_scores),
        "areas": _norm(area_scores),
    }


def analyze_session(
    text: str,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    normalize_scores: bool = True,
    ngram_n: int = 2,
    embedding: dict[str, Any] | None = None,
    *,
    psi_prev: dict[str, float] | None = None,
    apply_semantic_state: bool = True,
    apply_token_negation: bool = False,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
    per_concept_score_cap: float | None = None,
    use_log1p_concept_scores: bool = False,
    evidence_volume_normalize: bool = False,
    contradictions: list[dict[str, Any]] | None = None,
    uncertainty_package: dict[str, Any] | None = None,
    lexical_negation_summary: dict[str, Any] | None = None,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Полный пайплайн: текст сессии → токены → n-граммы → детекция маркеров (токены + фразы) → активация.

    Токены и n-граммы сопоставляются с Dict-A; совпадения дают (concept_id, weight), далее агрегация
    по концептам, семьям и областям.

    Для TFP runtime итоговые ``areas`` теперь всегда строятся по инвариантному пути:
    стабилизация концептов → hex-feedback → межзонное торможение → softmax.
    Старые линейные / max-norm значения остаются только в диагностических ключах.

    Возвращает:
    {
      "areas":   { "A3": 0.67, "A2": 0.54 },
      "families": { "A3_F6": 0.45, ... },
      "concepts": { "B_A3_F6_002": 0.33, ... }
    }

    Опционально: результат можно передать в interpret_session() (LEVEL 8) для клинической интерпретации:
      analysis = analyze_session(text); interpretation = interpret_session(analysis)

    Если передан embedding (например load_family_embedding_tfp()), после активации выполняется
    распространение по топологии (LEVEL 13): внутри области по зонам и по мостам между областями;
    в результате добавляется ключ "propagation_trace".
    """
    tokens = tokenize_text(text)
    normalized = normalize_tokens(tokens)
    # 1) Фразовые маркеры (приоритет): биграммы/триграммы по phrase_index (tuple lookup, O(n))
    pidx = phrase_index if phrase_index is not None else _get_phrase_index()
    phrase_matches = (
        detect_phrase_markers(
            tokens=normalized,
            phrase_index=pidx,
            apply_negation=apply_token_negation,
            negation_window=negation_window,
            negation_multiplier=negation_multiplier,
        )
        if pidx
        else []
    )
    phrase_concepts = {c for c, _ in phrase_matches}
    markers = list(phrase_matches)
    # 2) Строковые n-граммы в marker_index (доп. покрытие; без дублей по концептам)
    if ngram_n >= 1 and len(normalized) >= ngram_n:
        ngrams = build_ngrams(normalized, n=ngram_n)
        string_phrase = detect_phrase_markers(ngrams=ngrams, marker_index=marker_index)
        markers += [(c, w) for c, w in string_phrase if c not in phrase_concepts]
        phrase_concepts |= {c for c, _ in string_phrase}
    # 3) Одиночные токены: только концепты, не активированные фразой
    token_matches = detect_markers(
        normalized,
        marker_index=marker_index,
        apply_negation=apply_token_negation,
        negation_window=negation_window,
        negation_multiplier=negation_multiplier,
    )
    markers += [(c, w) for c, w in token_matches if c not in phrase_concepts]
    activation = build_invariant_activation(
        markers,
        token_count=len(normalized),
        concept_to_area_family=concept_to_area_family,
        embedding=embedding,
        psi_prev=psi_prev,
        apply_semantic_state=apply_semantic_state,
        contradictions=contradictions,
        uncertainty_package=uncertainty_package,
        lexical_negation_summary=lexical_negation_summary,
        contradiction_calibration=contradiction_calibration,
    )
    activation["runtime_compat"] = {
        "normalize_scores_requested": bool(normalize_scores),
        "per_concept_score_cap_requested": per_concept_score_cap,
        "use_log1p_concept_scores_requested": bool(use_log1p_concept_scores),
        "evidence_volume_normalize_requested": bool(evidence_volume_normalize),
        "invariant_runtime_path": True,
    }
    return activation


def analyze_session_enhanced(
    text: str,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    normalize_scores: bool = True,
    ngram_n: int = 2,
    embedding: dict[str, Any] | None = None,
    use_lemmatizer: bool = True,
    use_colloquial: bool = True,
    use_phrase_patterns: bool = True,
) -> dict[str, Any]:
    """
    Russian activation enhancement: lemmatize → token+lemma lookup (merged + colloquial) → phrase_patterns.

    Pipeline: text → tokenize → normalize → [lemmatize] → detect_markers(tokens) + detect_markers(lemmas)
    → detect_phrase_patterns(text) → phrase_markers (bigrams/trigrams) → activation → [propagation].

    Weights: token/lemma from dict (1.0), colloquial from dict (1.2), phrase pattern from dict (1.5).
    """
    from hesperia.nlp.lemmatizer import lemmatize_tokens
    from hesperia.nlp.phrase_detector import detect_phrase_patterns as detect_regex_patterns

    tokens = tokenize_text(text)
    normalized = normalize_tokens(tokens)
    if use_lemmatizer:
        try:
            lemmas = lemmatize_tokens(normalized)
        except Exception:
            lemmas = normalized
    else:
        lemmas = normalized

    if use_colloquial:
        midx = _get_merged_marker_index()
        if marker_index is not None:
            midx = dict(midx)
            for k, v in marker_index.items():
                midx.setdefault(k, []).extend(v)
    else:
        midx = marker_index if marker_index is not None else _get_marker_index()
    pidx = phrase_index if phrase_index is not None else _get_phrase_index()
    af = concept_to_area_family if concept_to_area_family is not None else _get_concept_to_af()

    phrase_concepts: set[str] = set()
    markers: list[tuple[str, float]] = []

    if use_phrase_patterns:
        pattern_matches = detect_regex_patterns(text)
        markers.extend(pattern_matches)
        phrase_concepts |= {c for c, _ in pattern_matches}

    if pidx and len(normalized) >= 2:
        phrase_matches = detect_phrase_markers(tokens=normalized, phrase_index=pidx)
        markers.extend((c, w) for c, w in phrase_matches if c not in phrase_concepts)
        phrase_concepts |= {c for c, _ in phrase_matches}
    if ngram_n >= 1 and len(normalized) >= ngram_n:
        ngrams = build_ngrams(normalized, n=ngram_n)
        string_phrase = detect_phrase_markers(ngrams=ngrams, marker_index=midx)
        markers.extend((c, w) for c, w in string_phrase if c not in phrase_concepts)
        phrase_concepts |= {c for c, _ in string_phrase}

    token_matches = detect_markers(normalized, marker_index=midx)
    markers.extend((c, w) for c, w in token_matches if c not in phrase_concepts)
    phrase_concepts |= {c for c, _ in token_matches}
    if lemmas != normalized:
        lemma_matches = detect_markers(lemmas, marker_index=midx)
        markers.extend((c, w) for c, w in lemma_matches if c not in phrase_concepts)

    activation = activate_concepts(markers, concept_to_area_family=af, normalize_scores=normalize_scores)
    if embedding is not None:
        from sphere.topology.activation_propagation import propagate_activation
        prop = propagate_activation(activation, embedding, propagation_trace=True)
        activation["families"] = prop["families"]
        activation["areas"] = prop["areas"]
        activation["propagation_trace"] = prop.get("propagation_trace", [])
    return activation


# LEVEL 15: speaker-weighted activation (patient = mental dynamics, therapist = intervention)
PATIENT_MARKER_WEIGHT = 1.0
THERAPIST_MARKER_WEIGHT = 0.5


def _markers_for_tokens(
    tokens: list[str],
    marker_index: dict[str, list[tuple[str, float]]] | None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None,
    ngram_n: int,
    *,
    apply_negation: bool = False,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
) -> list[tuple[str, float]]:
    """Collect (concept_id, weight) from phrase + ngram + token detection for one utterance."""
    phrase_concepts: set[str] = set()
    markers: list[tuple[str, float]] = []
    if phrase_index and len(tokens) >= 2:
        phrase_matches = detect_phrase_markers(
            tokens=tokens,
            phrase_index=phrase_index,
            apply_negation=apply_negation,
            negation_window=negation_window,
            negation_multiplier=negation_multiplier,
        )
        markers.extend(phrase_matches)
        phrase_concepts = {c for c, _ in phrase_matches}
    if ngram_n >= 1 and len(tokens) >= ngram_n:
        ngrams = build_ngrams(tokens, n=ngram_n)
        string_phrase = detect_phrase_markers(ngrams=ngrams, marker_index=marker_index)
        markers.extend((c, w) for c, w in string_phrase if c not in phrase_concepts)
        phrase_concepts |= {c for c, _ in string_phrase}
    token_matches = detect_markers(
        tokens,
        marker_index=marker_index,
        apply_negation=apply_negation,
        negation_window=negation_window,
        negation_multiplier=negation_multiplier,
    )
    markers.extend((c, w) for c, w in token_matches if c not in phrase_concepts)
    return markers


def analyze_session_speaker_aware(
    text: str,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    normalize_scores: bool = True,
    ngram_n: int = 2,
    embedding: dict[str, Any] | None = None,
    patient_weight: float = PATIENT_MARKER_WEIGHT,
    therapist_weight: float = THERAPIST_MARKER_WEIGHT,
    *,
    apply_token_negation: bool = True,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
) -> dict[str, Any]:
    """
    Multi-channel, role-weighted lexical analysis over structured dialogue.

    **Product semantics:** each utterance stream contributes lexical marker evidence scaled by
    a per-stream **weight** (defaults: ``patient_weight``, ``therapist_weight``). The combined
    output is **channel-weighted lexical evidence**—the same invariant marker→concept path as
    single-stream analysis, with deterministic aggregation across streams. This is not a clinical
    or care-setting interpretation layer; sealed product narrative stays in engine docs
    (``HESPERIA_v0_5_ENGINE_DYNAMICS.md`` §8).

    Pipeline: ``parse_session_dialogue`` → tokenize per utterance → ``detect_markers`` (and
    optional phrase/ngram paths) → weighted activation per stream → optional propagation.

    Returns:
    {
      "areas": {}, "families": {}, "concepts": {},   # combined weighted
      "speaker_activation": {
        "patient":  { "areas": {}, "families": {}, "concepts": {} },
        "therapist": { "areas": {}, "families": {}, "concepts": {} }
      }
    }
    """
    from hesperia.nlp.session_structure import parse_session_dialogue

    utterances = parse_session_dialogue(text)
    pidx = phrase_index if phrase_index is not None else _get_phrase_index()
    midx = marker_index if marker_index is not None else _get_marker_index()
    af = concept_to_area_family if concept_to_area_family is not None else _get_concept_to_af()

    combined_markers: list[tuple[str, float]] = []
    patient_markers: list[tuple[str, float]] = []
    therapist_markers: list[tuple[str, float]] = []
    patient_tokens = 0
    therapist_tokens = 0
    direction_markers: dict[str, list[tuple[str, float]]] = {
        "patient_to_therapist": [],
        "therapist_to_patient": [],
        "patient_to_third": [],
    }
    direction_tokens: dict[str, int] = {
        "patient_to_therapist": 0,
        "therapist_to_patient": 0,
        "patient_to_third": 0,
    }

    for u in utterances:
        raw = _markers_for_tokens(
            u.tokens,
            midx,
            pidx,
            ngram_n,
            apply_negation=apply_token_negation,
            negation_window=negation_window,
            negation_multiplier=negation_multiplier,
        )
        w = patient_weight if u.speaker == "patient" else therapist_weight
        direction_key = f"{u.speaker}_to_{u.target}"
        if direction_key not in direction_markers:
            direction_markers[direction_key] = []
            direction_tokens[direction_key] = 0
        direction_tokens[direction_key] += len(u.tokens)
        if u.speaker == "patient":
            patient_tokens += len(u.tokens)
        else:
            therapist_tokens += len(u.tokens)
        for cid, weight in raw:
            scaled = weight * w
            combined_markers.append((cid, scaled))
            direction_markers[direction_key].append((cid, scaled))
            if u.speaker == "patient":
                patient_markers.append((cid, weight * patient_weight))
            else:
                therapist_markers.append((cid, weight * therapist_weight))

    activation = build_invariant_activation(
        combined_markers,
        token_count=patient_tokens + therapist_tokens,
        concept_to_area_family=af,
        embedding=embedding,
        apply_semantic_state=True,
    )
    activation["speaker_activation"] = {
        "patient": build_invariant_activation(
            patient_markers,
            token_count=patient_tokens,
            concept_to_area_family=af,
            apply_semantic_state=False,
        ),
        "therapist": build_invariant_activation(
            therapist_markers,
            token_count=therapist_tokens,
            concept_to_area_family=af,
            apply_semantic_state=False,
        ),
    }
    activation["activation_by_direction"] = {
        key: build_invariant_activation(
            markers,
            token_count=direction_tokens.get(key, 0),
            concept_to_area_family=af,
            apply_semantic_state=False,
        )
        for key, markers in direction_markers.items()
        if markers
    }
    activation["role_direction"] = {
        "patient_to_therapist": {"speaker": "patient", "target": "therapist"},
        "therapist_to_patient": {"speaker": "therapist", "target": "patient"},
        "patient_to_third": {"speaker": "patient", "target": "third"},
    }
    activation["runtime_compat"] = {
        "normalize_scores_requested": bool(normalize_scores),
        "speaker_weighting_active": True,
        "patient_weight": float(patient_weight),
        "therapist_weight": float(therapist_weight),
        "invariant_runtime_path": True,
    }

    return activation
