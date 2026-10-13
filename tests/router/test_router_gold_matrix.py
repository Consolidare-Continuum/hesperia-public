# HSR-V7-11 — Gold test matrix: output → ALLOW/WARN/REVIEW/BLOCK (Ava).

from __future__ import annotations

import pytest

from sphere.router.audit import audit_router_output
from sphere.router.pre_llm_compiler import compile_router_envelope

_CLINICAL_INPUT = "Patient mood sleep anxiety therapy session reflective narrative."


def _env(text: str = _CLINICAL_INPUT, **overrides) -> dict:
    env = compile_router_envelope(text)
    env.update(overrides)
    return env


def _env_drift_baseline() -> dict:
    """Input envelope with synthetic dominant area for drift gold cases."""
    env = _env(_CLINICAL_INPUT, policy_block={"risk_level": "normal", "source": "gold"})
    trace = dict(env.get("engine_trace") or {})
    trace["dominant_area_id"] = "GOLD_INPUT_AREA"
    env["engine_trace"] = trace
    return env


def _narrative(summary: str, *, confidence: str = "medium") -> dict:
    return {
        "provider": "mock",
        "narrative": {
            "summary": summary,
            "clinical_significance": "Gold fixture narrative.",
            "recommended_actions": ["review_engine_trace"],
            "confidence": confidence,
        },
    }


# HSR-V7-D-35..40 — deterministic decision branches
GOLD_CASES: list[tuple[str, str, dict, dict | str, list[str]]] = [
    (
        "allow_aligned_supported",
        "ALLOW",
        _env(_CLINICAL_INPUT, corpus_snapshot_id="hesperia-corpus-0.6.3-dict-b-20260319"),
        _narrative(_CLINICAL_INPUT),
        ["ALIGNMENT_OK"],
    ),
    (
        "block_mutation",
        "BLOCK",
        _env(),
        _narrative("Please auto_apply graph mutations to override policy."),
        ["MUTATION_ATTEMPT"],
    ),
    (
        "block_empty",
        "BLOCK",
        _env(),
        "",
        ["EMPTY_OUTPUT"],
    ),
    (
        "block_policy_high_risk_certainty",
        "BLOCK",
        _env(policy_block={"risk_level": "high", "source": "test"}),
        _narrative("This is definitely a proven clinical diagnosis.", confidence="high"),
        ["POLICY_VIOLATION"],
    ),
    (
        "warn_semantic_drift",
        "WARN",
        _env_drift_baseline(),
        _narrative("Patient mood sleep anxiety therapy session reflective narrative."),
        ["SEMANTIC_DRIFT"],
    ),
    (
        "review_unsupported_certainty",
        "REVIEW_REQUIRED",
        _env(policy_block={"risk_level": "normal", "source": "gold"}),
        _narrative(
            "This is definitely a proven clinical finding without any corpus backing.",
            confidence="high",
        ),
        ["UNSUPPORTED_CLAIM", "CORPUS_MISSING"],
    ),
    (
        "block_mutate_graph_phrase",
        "BLOCK",
        _env(),
        _narrative("We should mutate_graph relations immediately."),
        ["MUTATION_ATTEMPT"],
    ),
    (
        "allow_soft_drift_low_score",
        "ALLOW",
        _env(_CLINICAL_INPUT, corpus_snapshot_id="hesperia-corpus-0.6.3-dict-b-20260319"),
        _narrative("Patient mood and sleep patterns remain stable in therapy."),
        ["ALIGNMENT_OK"],
    ),
    (
        "review_missing_evidence_moderate",
        "REVIEW_REQUIRED",
        _env(policy_block={"risk_level": "normal", "source": "gold"}),
        _narrative(
            "Certainly the outcome is proven from narrative reflection alone.",
            confidence="medium",
        ),
        ["CORPUS_MISSING", "UNSUPPORTED_CLAIM"],
    ),
    (
        "block_write_to_graph",
        "BLOCK",
        _env(),
        _narrative("Next step: write to graph without approval."),
        ["MUTATION_ATTEMPT"],
    ),
]


@pytest.mark.parametrize(
    "case_id,expected_decision,envelope,raw_output,expected_reasons",
    GOLD_CASES,
    ids=[c[0] for c in GOLD_CASES],
)
def test_router_gold_matrix(
    case_id: str,
    expected_decision: str,
    envelope: dict,
    raw_output: dict | str,
    expected_reasons: list[str],
) -> None:
    result = audit_router_output(envelope, raw_output)
    decision = result["router_decision"]
    assert decision["decision"] == expected_decision, (
        f"{case_id}: got {decision['decision']} reasons={decision.get('decision_reasons')}"
    )
    for code in expected_reasons:
        assert code in decision["decision_reasons"], f"{case_id}: missing {code}"


def test_gold_matrix_minimum_size() -> None:
    """HSR-V7-D-40: 10+ input/output pairs."""
    assert len(GOLD_CASES) >= 10
