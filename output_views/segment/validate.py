"""T04 — jsonschema validation for iteration_segment_openai_v1."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "iteration_segment_openai_v1.schema.json"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    raw = _SCHEMA_PATH.read_text(encoding="utf-8")
    schema = json.loads(raw)
    return Draft202012Validator(schema)


def validate_iteration_segment_openai_v1(obj: dict[str, Any]) -> None:
    """Raise jsonschema.ValidationError if invalid."""
    v = _validator()
    errors = sorted(v.iter_errors(obj), key=lambda e: e.path)
    if errors:
        raise errors[0]
