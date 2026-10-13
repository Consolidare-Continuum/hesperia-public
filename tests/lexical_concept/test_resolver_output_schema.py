from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "assets" / "schemas" / "lexical_concept" / "resolver_output.schema.json"


def test_resolver_output_schema_accepts_unresolved_span() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "source_text_span": "split state",
        "source_char_start": 0,
        "source_char_end": 11,
        "normalized_span": "split state",
        "candidate_concepts": ["C-1", "C-2"],
        "candidate_scores": {"C-1": 0.8, "C-2": 0.8},
        "winning_concept_id": None,
        "winning_reason_codes": [],
        "rejected_reason_codes": ["tie_unresolved"],
        "rule_trace": ["phrase-first", "stable-tiebreak"],
        "unresolved_reason": "tie_after_all_rules",
        "mode": "clinical_speech",
        "version": "v0.6.0"
    }
    errors = list(validator.iter_errors(payload))
    assert errors == []


def test_resolver_output_schema_accepts_audit_block() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "source_text_span": "x",
        "source_char_start": 0,
        "source_char_end": 1,
        "normalized_span": "x",
        "candidate_concepts": ["C-1"],
        "candidate_scores": {"C-1": 1.0},
        "winning_concept_id": "C-1",
        "winning_reason_codes": ["top_score_unique"],
        "rejected_reason_codes": [],
        "rule_trace": ["phrase-first"],
        "audit": {"candidates_detail": [], "tie_break_rule": "specificity_rank_desc_then_concept_id_lex"},
        "mode": "clinical_speech",
        "version": "v0.6.0",
    }
    assert list(validator.iter_errors(payload)) == []

