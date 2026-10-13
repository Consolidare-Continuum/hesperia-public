from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "assets" / "schemas" / "lexical_concept" / "dict_a.schema.json"


def test_dict_a_schema_accepts_minimal_valid_entry() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {
        "entry_id": "A-1",
        "surface_form": "split",
        "normalized_form": "split",
        "match_type": "exact",
        "candidate_concept_ids": ["C-1"],
        "priority": 10,
        "version": "v0.6.0"
    }
    errors = list(validator.iter_errors(payload))
    assert errors == []


def test_dict_a_schema_rejects_missing_required() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = {"entry_id": "A-2"}
    errors = list(validator.iter_errors(payload))
    assert errors

