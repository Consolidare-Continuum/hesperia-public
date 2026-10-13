# HSR-V7-C-18 / D-16 / D-17 / D-20 — JSON Schema + compiler gold tests.

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from sphere.router.audit import audit_router_output
from sphere.router.pre_llm_compiler import compile_router_envelope
from sphere.router.prompt_envelope import build_prompt_envelope

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "assets" / "schemas" / "router"
_GOLD_TEXT = (
    "TFP reflective narrative: patient mood regulation sleep anxiety therapy session."
)


def _load_schema(name: str) -> dict:
    return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _gold_input_envelope() -> dict:
    return compile_router_envelope(_GOLD_TEXT, corpus_snapshot_id="hesperia-corpus-0.6.5-gold")


@pytest.mark.parametrize(
    "schema_file,builder",
    [
        ("router_input_envelope_v0_1.schema.json", _gold_input_envelope),
        (
            "router_prompt_envelope_v0_1.schema.json",
            lambda: build_prompt_envelope(_gold_input_envelope()),
        ),
    ],
)
def test_router_schema_validates(schema_file: str, builder) -> None:
    schema = _load_schema(schema_file)
    instance = builder()
    Draft202012Validator(schema).validate(instance)


def test_output_audit_schema_validates() -> None:
    env = _gold_input_envelope()
    raw = {
        "narrative": {
            "summary": _GOLD_TEXT,
            "clinical_significance": "Gold fixture aligned narrative.",
            "recommended_actions": ["review_engine_trace"],
            "confidence": "medium",
        },
    }
    result = audit_router_output(env, raw)
    schema = _load_schema("router_output_audit_v0_1.schema.json")
    Draft202012Validator(schema).validate(result["audit"])


def test_compiler_integration_matches_gold_fields() -> None:
    """HSR-V7-D-16: known TFP input → envelope fields stable."""
    env = _gold_input_envelope()
    assert env["schema"] == "hesperia.router_input_envelope.v0_1"
    assert env["corpus_snapshot_id"] == "hesperia-corpus-0.6.5-gold"
    assert env["engine_trace"].get("trace")
    assert len(env["router_fingerprint"]) >= 16
    prompt = build_prompt_envelope(env)
    assert "input_text" not in prompt
    assert prompt["input_hash"] == env["input_hash"]


def test_compiler_determinism_identical_fingerprint() -> None:
    """HSR-V7-D-17: same input → identical router_fingerprint."""
    a = compile_router_envelope(_GOLD_TEXT, corpus_snapshot_id="hesperia-corpus-0.6.5-gold")
    b = compile_router_envelope(_GOLD_TEXT, corpus_snapshot_id="hesperia-corpus-0.6.5-gold")
    assert a["router_fingerprint"] == b["router_fingerprint"]
    assert a["input_hash"] == b["input_hash"]


def test_compiler_perf_under_2s() -> None:
    """HSR-V7-D-20: envelope compilation perf baseline (dev VM cold path)."""
    start = time.perf_counter()
    compile_router_envelope(_GOLD_TEXT)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 2000, f"compile_router_envelope {elapsed_ms:.1f}ms"
