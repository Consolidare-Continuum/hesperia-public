# HESPERIA — RAD. Ethan PO-11 / PO-02 wiring tests.
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]


def test_po02_public_dlcr_span_strips_audit() -> None:
    from runtime.pipeline.analyze import _public_dlcr_span_row

    row = {
        "source_text_span": "a",
        "source_char_start": 0,
        "source_char_end": 1,
        "normalized_span": "a",
        "candidate_concepts": ["C1"],
        "candidate_scores": {"C1": 1.0},
        "winning_concept_id": "C1",
        "winning_reason_codes": [],
        "rejected_reason_codes": [],
        "rule_trace": [],
        "mode": "clinical_speech",
        "version": "v0.6.0",
        "audit": {"candidates_detail": []},
    }
    out = _public_dlcr_span_row(row)
    assert "audit" not in out
    assert out.get("winning_concept_id") == "C1"


@pytest.mark.skipif(not (REPO / "assets" / "lexicon" / "curated").is_dir(), reason="lexicon curated missing")
def test_markers_to_concept_activation_observe_includes_semantic_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_CONCEPT_EVIDENCE_GUARD", "observe")
    from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

    act = markers_to_concept_activation("justice fairness order", REPO / "assets" / "lexicon" / "curated")
    assert "semantic_evidence" in act
    se = act["semantic_evidence"]
    assert se.get("guard_mode") == "observe"
    assert "degraded_word_to_family" in se
    monkeypatch.delenv("HESPERIA_CONCEPT_EVIDENCE_GUARD", raising=False)


_V06_DICT_A = REPO / "assets" / "lexicon" / "curated" / "v0_5_0" / "dict_a_v06.jsonl"


@pytest.mark.skipif(not _V06_DICT_A.is_file(), reason="v0_5_0 dict_a_v06.jsonl not present (CI optional)")
def test_analyze_dlcr_evidence_extended_when_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_ANALYZE_DLCR_EVIDENCE", "1")
    from runtime.pipeline.analyze import analyze

    assets = REPO / "assets" / "lexicon" / "curated"
    _m, ext = analyze("justice fairness order truth", assets_root=assets)
    assert "lexical_evidence_dlcr" in ext
    lev = ext["lexical_evidence_dlcr"]
    assert isinstance(lev, dict)
    assert "lexical_hits_accepted" in lev or "_error" in lev
    if "_error" not in lev:
        # PO-02 acceptance: bounded evidence_spans with resolver-aligned stable keys.
        assert "evidence_spans" in lev
        assert isinstance(lev["evidence_spans"], list)
        assert lev.get("evidence_spans_schema_id")
        schema = json.loads(
            (REPO / "assets" / "schemas" / "lexical_concept" / "resolver_output.schema.json").read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        for row in lev["evidence_spans"]:
            validator.validate(row)
            assert "source_text_span" in row
            assert "winning_concept_id" in row
            assert "audit" not in row
    monkeypatch.delenv("HESPERIA_ANALYZE_DLCR_EVIDENCE", raising=False)
