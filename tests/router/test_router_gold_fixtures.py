# HSR-V7-C-19 / C-20 — Baseline gold fixtures (Ava).

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sphere.router.audit import audit_router_output
from sphere.router.pre_llm_compiler import compile_router_envelope
from sphere.router.prompt_envelope import build_prompt_envelope

_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "router"
_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "assets" / "schemas" / "router"

_TFP_GOLD = (
    "TFP gold fixture: reflective mood sleep anxiety narrative for router envelope baseline."
)


def _build_gold_input_fixture() -> dict:
    return compile_router_envelope(
        _TFP_GOLD,
        corpus_snapshot_id="hesperia-corpus-0.6.5-gold-fixture",
    )


def _build_gold_audit_fixture() -> dict:
    env = _build_gold_input_fixture()
    raw = {
        "provider": "mock",
        "narrative": {
            "summary": _TFP_GOLD,
            "clinical_significance": "Consistent with sealed engine trace review.",
            "recommended_actions": ["review_engine_trace"],
            "confidence": "medium",
        },
    }
    return audit_router_output(env, raw)


def test_gold_input_envelope_fixture_file() -> None:
    """C-19: baseline RouterInputEnvelope from known TFP statement."""
    env = _build_gold_input_fixture()
    schema = json.loads(
        (_SCHEMA_DIR / "router_input_envelope_v0_1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(env)
    prompt = build_prompt_envelope(env)
    assert "input_text" not in prompt
    fixture_path = _FIXTURE_DIR / "gold_router_input_envelope_v0_1.json"
    if fixture_path.exists():
        on_disk = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert on_disk["input_hash"] == env["input_hash"]
        assert on_disk["router_fingerprint"] == env["router_fingerprint"]


def test_gold_output_audit_fixture() -> None:
    """C-20: baseline RouterOutputAudit from known LLM output."""
    result = _build_gold_audit_fixture()
    audit = result["audit"]
    schema = json.loads(
        (_SCHEMA_DIR / "router_output_audit_v0_1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(audit)
    assert result["router_decision"]["decision"] in (
        "ALLOW",
        "WARN",
        "REVIEW_REQUIRED",
        "BLOCK",
    )
    fixture_path = _FIXTURE_DIR / "gold_router_output_audit_v0_1.json"
    if fixture_path.exists():
        on_disk = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert on_disk.get("schema") == audit["schema"]
