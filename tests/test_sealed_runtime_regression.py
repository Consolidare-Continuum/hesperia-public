# HESPERIA — Sealed runtime regression tests.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Fixed corpus: tests/sealed_runtime_inputs/ (10–20 texts).
# During release: analyze each, compare pairs, batch-analyze. Verify:
#   - deterministic output
#   - schema validity (validate_against_public_schema)
#   - no forbidden keys in output

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Forbidden terms in serialized output. Use word-boundary patterns where a substring would
# false-positive on approved public tokens (e.g. "hex_microcell" must not trip "hex").
_FORBIDDEN_SUBSTRINGS = (
    "topology",
    "area11",
    "family240",
    "coordinates",
    "vector3",
    "side_id",
    "layer_",
    "internal_layer",
)
_FORBIDDEN_WORD_RE = re.compile(
    r"\b(?:sphere|hex|bridge)\b",
    re.IGNORECASE,
)


def _inputs_dir() -> Path:
    return Path(__file__).resolve().parent / "sealed_runtime_inputs"


def _sample_texts() -> list[str]:
    d = _inputs_dir()
    if not d.is_dir():
        return []
    texts = []
    for f in sorted(d.glob("*.txt")):
        texts.append(f.read_text(encoding="utf-8").strip())
    return texts


def _assets_root() -> Path:
    repo = Path(__file__).resolve().parents[1]
    cur = repo / "assets" / "lexicon" / "curated"
    return cur if cur.is_dir() else repo / "assets" / "lexicon" / "curated"


@pytest.fixture(scope="module")
def assets_root():
    return _assets_root()


@pytest.fixture(scope="module")
def sample_texts():
    return _sample_texts()


def test_sealed_runtime_inputs_exist():
    """Regression corpus must exist and have 10–20 texts."""
    texts = _sample_texts()
    assert len(texts) >= 10, "sealed_runtime_inputs should have at least 10 sample texts"
    assert len(texts) <= 25, "sealed_runtime_inputs should have at most ~20 texts"


def test_analyze_deterministic(sample_texts, assets_root):
    """Same input → same output (analyze)."""
    if not sample_texts:
        pytest.skip("no sealed_runtime_inputs")
    from runtime.services.analysis_service import run_structural_analysis
    text = sample_texts[0]
    r1 = run_structural_analysis(text, assets_root=assets_root, stages="full")
    r2 = run_structural_analysis(text, assets_root=assets_root, stages="full")
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_analyze_schema_valid(sample_texts, assets_root):
    """Analysis output passes schema_guard (no forbidden keys)."""
    if not sample_texts:
        pytest.skip("no sealed_runtime_inputs")
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.shipping.schema_guard import validate_against_public_schema
    for text in sample_texts[:5]:
        result = run_structural_analysis(text, assets_root=assets_root, stages="full")
        validate_against_public_schema(result)


def test_analyze_no_forbidden_in_output(sample_texts, assets_root):
    """Serialized analysis output contains no forbidden terms."""
    if not sample_texts:
        pytest.skip("no sealed_runtime_inputs")
    from runtime.services.analysis_service import run_structural_analysis
    out = run_structural_analysis(sample_texts[0], assets_root=assets_root, stages="full")
    s = json.dumps(out)
    assert _FORBIDDEN_WORD_RE.search(s) is None, "forbidden word (sphere|hex|bridge) in output"
    sl = s.lower()
    for bad in _FORBIDDEN_SUBSTRINGS:
        assert bad not in sl, f"forbidden term '{bad}' in output"


def test_compare_deterministic(sample_texts, assets_root):
    """Compare on same pair twice → same output."""
    if len(sample_texts) < 2:
        pytest.skip("need at least 2 texts")
    from runtime.services.analysis_service import run_structural_analysis
    t1, t2 = sample_texts[0], sample_texts[1]
    r1a = run_structural_analysis(t1, assets_root=assets_root, stages="full")
    r2a = run_structural_analysis(t2, assets_root=assets_root, stages="full")
    r1b = run_structural_analysis(t1, assets_root=assets_root, stages="full")
    r2b = run_structural_analysis(t2, assets_root=assets_root, stages="full")
    d1 = (r1a.get("L7") or {}), (r2a.get("L7") or {})
    d2 = (r1b.get("L7") or {}), (r2b.get("L7") or {})
    dom1a = (r1a.get("usf") or {}).get("raw_metrics") or {}
    dom2a = (r2a.get("usf") or {}).get("raw_metrics") or {}
    dom1b = (r1b.get("usf") or {}).get("raw_metrics") or {}
    dom2b = (r2b.get("usf") or {}).get("raw_metrics") or {}
    comp_a = {
        "result1_trust": d1[0].get("OUTPUT_TRUST_TAG"),
        "result2_trust": d1[1].get("OUTPUT_TRUST_TAG"),
        "dominant_match": _same_dominant(dom1a, dom2a),
        "confidence_delta": _confidence_delta(d1[0], d1[1]),
    }
    comp_b = {
        "result1_trust": d2[0].get("OUTPUT_TRUST_TAG"),
        "result2_trust": d2[1].get("OUTPUT_TRUST_TAG"),
        "dominant_match": _same_dominant(dom1b, dom2b),
        "confidence_delta": _confidence_delta(d2[0], d2[1]),
    }
    assert json.dumps(comp_a, sort_keys=True) == json.dumps(comp_b, sort_keys=True)


def _same_dominant(m1: dict, m2: dict) -> bool:
    v1 = m1.get("macro_domain_vector") or m1.get("dominant_macro_domain")
    v2 = m2.get("macro_domain_vector") or m2.get("dominant_macro_domain")
    if isinstance(v1, list) and isinstance(v2, list):
        i1 = max(range(len(v1)), key=lambda i: v1[i]) if v1 else -1
        i2 = max(range(len(v2)), key=lambda i: v2[i]) if v2 else -1
        return i1 == i2
    return False


def _confidence_delta(d1: dict, d2: dict) -> str:
    c1 = d1.get("TRUST_TIER") or d1.get("OUTPUT_TRUST_TAG") or ""
    c2 = d2.get("TRUST_TIER") or d2.get("OUTPUT_TRUST_TAG") or ""
    return "same" if c1 == c2 else "different"


def test_batch_deterministic(sample_texts, assets_root):
    """Batch analyze same list twice → same outputs."""
    if not sample_texts:
        pytest.skip("no sealed_runtime_inputs")
    from runtime.services.analysis_service import run_structural_analysis_batch
    batch = sample_texts[:5]
    r1 = run_structural_analysis_batch(batch, assets_root=assets_root)
    r2 = run_structural_analysis_batch(batch, assets_root=assets_root)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


def test_batch_schema_valid(sample_texts, assets_root):
    """Batch output passes schema_guard."""
    if not sample_texts:
        pytest.skip("no sealed_runtime_inputs")
    from runtime.services.analysis_service import run_structural_analysis_batch
    from runtime.shipping.schema_guard import validate_against_public_schema
    results = run_structural_analysis_batch(sample_texts[:5], assets_root=assets_root)
    validate_against_public_schema(results)
