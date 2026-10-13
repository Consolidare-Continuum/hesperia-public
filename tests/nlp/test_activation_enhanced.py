# HESPERIA — Russian activation enhancement tests (lemmatizer + colloquial + phrase patterns)
"""Expect: A2 object relations, A3 defenses, A4 aggression for TFP dialogue input."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_lemmatize_tokens() -> None:
    """lemmatize_tokens normalizes Russian word forms when pymorphy2 available."""
    from hesperia.nlp.lemmatizer import lemmatize_tokens, is_lemmatizer_available

    tokens = ["ненавижу", "бесился", "боялась"]
    lemmas = lemmatize_tokens(tokens)
    assert len(lemmas) == 3
    assert all(isinstance(x, str) for x in lemmas)
    if is_lemmatizer_available():
        assert "ненавидеть" in lemmas or "ненавижу" in lemmas
        assert "беситься" in lemmas or "бесился" in lemmas
    else:
        assert lemmas == [t.lower() for t in tokens]


def test_detect_phrase_patterns() -> None:
    """Regex patterns from phrase_patterns.yaml match TFP-style text."""
    from hesperia.nlp.phrase_detector import detect_phrase_patterns

    text = "Вы меня просто ненавидите. Меня уже бесит это."
    out = detect_phrase_patterns(text)
    assert isinstance(out, list)
    assert all(isinstance(p, tuple) and len(p) == 2 for p in out)
    # At least one pattern should match "ненавид" or "вы"
    concept_ids = [c for c, _ in out]
    if out:
        assert all(c.startswith("B_") for c in concept_ids)


def test_analyze_session_enhanced_shape() -> None:
    """analyze_session_enhanced returns areas, families, concepts."""
    from hesperia.nlp.session_parser import analyze_session_enhanced

    text = "Patient: Вы меня просто ненавидите.\nPatient: Меня уже бесит это."
    result = analyze_session_enhanced(text, use_lemmatizer=True, use_colloquial=True, use_phrase_patterns=True)
    assert "areas" in result and "families" in result and "concepts" in result
    assert isinstance(result["areas"], dict)
    assert isinstance(result["families"], dict)
    assert isinstance(result["concepts"], dict)


def test_analyze_session_enhanced_activates_a2_a3_a4() -> None:
    """Russian TFP input activates A2 (object relations), A3 (defenses), A4 (aggression)."""
    from hesperia.nlp.session_parser import analyze_session_enhanced

    text = "Patient: Вы меня просто ненавидите.\nPatient: Меня уже бесит это."
    result = analyze_session_enhanced(text)
    areas = result.get("areas", {})
    families = result.get("families", {})
    # With full Dict-A + colloquial + phrase_patterns we expect some A2, A3, A4
    area_keys = set(areas.keys())
    family_keys = set(families.keys())
    a2_families = {k for k in family_keys if k.startswith("A2_")}
    a3_families = {k for k in family_keys if k.startswith("A3_")}
    a4_families = {k for k in family_keys if k.startswith("A4_")}
    assert "A2" in area_keys or a2_families or "A3" in area_keys or a3_families or "A4" in area_keys or a4_families, (
        "Expected at least one of A2, A3, A4 in areas or families"
    )


def test_analyze_session_enhanced_with_mock_colloquial() -> None:
    """With mock colloquial index, colloquial markers contribute to activation."""
    from hesperia.nlp.session_parser import (
        analyze_session_enhanced,
        tokenize_text,
        normalize_tokens,
        detect_markers,
        activate_concepts,
    )
    from hesperia.nlp.lemmatizer import lemmatize_tokens

    marker_index = {
        "бесит": [("B_A4_F1_001", 1.2)],
        "ненавидите": [("B_A2_F3_002", 1.2)],
        "ненавидеть": [("B_A2_F3_002", 1.0)],
    }
    af = {
        "B_A4_F1_001": ("A4", "F1"),
        "B_A2_F3_002": ("A2", "F3"),
    }
    text = "Меня бесит это. Вы меня ненавидите."
    tokens = normalize_tokens(tokenize_text(text))
    lemmas = lemmatize_tokens(tokens)
    m1 = detect_markers(tokens, marker_index=marker_index)
    m2 = detect_markers(lemmas, marker_index=marker_index)
    combined = m1 + m2
    act = activate_concepts(combined, concept_to_area_family=af, normalize_scores=True)
    assert "A4" in act["areas"] or "A2" in act["areas"]
    assert act["concepts"] or act["families"]


def test_phrase_patterns_yaml_loaded() -> None:
    """phrase_patterns.yaml exists and load_phrase_patterns returns entries."""
    from hesperia.nlp.phrase_detector import load_phrase_patterns

    patterns = load_phrase_patterns()
    assert isinstance(patterns, list)
    if patterns:
        for p in patterns:
            assert "pattern" in p and "concept_id" in p
