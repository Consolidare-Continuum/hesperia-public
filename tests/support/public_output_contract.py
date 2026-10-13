# HESPERIA — Lightweight semantic contract for canonical structural JSON (product path).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any

from hesperia.system.version import structural_pipeline_version

# Envelope + layer buckets after attach_public_output_metadata + canonical multiscale projection.
_REQUIRED_TOP_LEVEL: frozenset[str] = frozenset(
    {
        "system_version",
        "build_id",
        "schema_version",
        "calibration_profile",
        "pipeline_version",
        "run",
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "L6",
        "L7",
        "L8",
        "L9",
        "usf",
        "diagnostics",
        "multiscale_signals",
    }
)

_L7_REQUIRED: frozenset[str] = frozenset(
    {
        "OUTPUT_TRUST_TAG",
        "TRUST_TIER",
        "DECISION_STATUS_CODE",
        "SYSTEM_CONFIDENCE_SCORE",
    }
)


def assert_multiscale_magnitude_bounds(out: dict[str, Any]) -> None:
    """Bounded physics checks — catches silent rescaling without pinning exact floats."""
    ms = out.get("multiscale_signals")
    assert isinstance(ms, dict), "multiscale_signals must be a dict"
    h = ms.get("hspr_index")
    assert isinstance(h, (int, float)), "hspr_index must be numeric"
    hf = float(h)
    assert -1e-12 <= hf <= 1.0 + 1e-12, f"hspr_index out of [0,1]: {h!r}"

    ps = ms.get("product_signals")
    assert isinstance(ps, dict) and len(ps) > 0, "product_signals must be a non-empty dict"
    for k, v in ps.items():
        assert isinstance(v, (int, float)), f"product_signals[{k!r}] must be numeric"
        fv = float(v)
        assert fv < 1.5, f"product_signals[{k!r}] exceeds sanity upper bound: {v!r}"
        assert fv >= -1e-9, f"product_signals[{k!r}] unexpected negative magnitude: {v!r}"

    L7 = out.get("L7") or {}
    sc = L7.get("SYSTEM_CONFIDENCE_SCORE")
    assert isinstance(sc, (int, float)), "L7.SYSTEM_CONFIDENCE_SCORE must be numeric"
    sf = float(sc)
    assert -1e-12 <= sf <= 1.0 + 1e-12, f"SYSTEM_CONFIDENCE_SCORE out of [0,1]: {sc!r}"

    usf = out.get("usf") or {}
    rm = usf.get("raw_metrics") or {}
    mdv = rm.get("macro_domain_vector")
    # Default core = length 12; optional ten-area module = length 10.
    if isinstance(mdv, list) and len(mdv) in (10, 12):
        for i, x in enumerate(mdv):
            assert isinstance(x, (int, float)), f"macro_domain_vector[{i}] must be numeric"
            xf = float(x)
            assert -1e-9 <= xf <= 1.0 + 1e-9, f"macro_domain_vector[{i}] out of [0,1]: {x!r}"
        s = sum(float(x) for x in mdv)
        # Low-signal inputs may yield a near-zero vector; when mass is present it must be normalized.
        if s > 1e-6:
            assert 0.98 <= s <= 1.02, f"macro_domain_vector must sum to ~1.0 when non-trivial, got {s}"
    elif isinstance(mdv, list):
        raise AssertionError(
            f"macro_domain_vector length must be 12 (default) or 10 (ten-area module), got {len(mdv)}"
        )

def assert_canonical_structural_json_contract(out: dict[str, Any]) -> None:
    """
    Explicit behavioral shape check (not a full JSON Schema validation).
    Fails on silent removal/renames of shipping-critical fields.
    """
    missing = _REQUIRED_TOP_LEVEL - frozenset(out.keys())
    assert not missing, f"missing top-level keys: {sorted(missing)}"

    assert out.get("pipeline_version") == structural_pipeline_version(), (
        f"pipeline_version mismatch: {out.get('pipeline_version')!r} != {structural_pipeline_version()!r}"
    )

    L7 = out.get("L7")
    assert isinstance(L7, dict), "L7 must be a dict"
    missing_l7 = _L7_REQUIRED - frozenset(L7.keys())
    assert not missing_l7, f"missing L7 keys: {sorted(missing_l7)}"

    ms = out.get("multiscale_signals")
    assert isinstance(ms, dict), "multiscale_signals must be a dict"
    assert "product_signals" in ms
    assert "hspr_index" in ms

    L1 = out.get("L1")
    assert isinstance(L1, dict) and L1.get("CANONICAL_PIPELINE") == "sealed_multiscale_v1"

    assert_multiscale_magnitude_bounds(out)

    from runtime.shipping.schema_guard import validate_against_public_schema

    validate_against_public_schema(out)
