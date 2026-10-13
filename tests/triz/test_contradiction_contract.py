# HESPERIA — Contradiction contract validation (v0.5.8 task10).

from __future__ import annotations

from typing import Any


def _session_payload(session_id: str = "s1") -> dict[str, Any]:
    cpkg = {
        "raw_contradiction_load": 0.6,
        "effective_contradiction_load": 0.52,
        "contradiction_confidence_mean": 0.7,
        "global_contradiction_load": 0.52,
        "cross_area_contradiction_mass": 0.4,
        "area_contradiction_pressure": {"A1": 0.5},
        "family_contradiction_pressure": {"A1_F1": 0.5},
        "family_fragmentation_summary": {"global_family_fragmentation": 0.2},
        "family_cross_area_bridge_mass": 0.25,
        "family_intra_area_conflict_mass": 0.3,
        "segment_contradiction_loads": [{"segment_id": 0, "contradiction_load": 0.45}],
        "transition_pressure": [0.2],
        "activation_conflict_load": 0.48,
        "latent_conflict_load": 0.5,
        "uncertainty_adjusted_conflict_index": 0.46,
        "lexical_semantic_conflict_split": {
            "likely_lexical": 0.2,
            "likely_conceptual_ambiguity": 0.3,
            "likely_semantic_real": 0.5,
        },
        "runtime_vs_calibration_conflict_split": {
            "likely_runtime_real": 0.6,
            "likely_calibration_pathology": 0.2,
        },
        "contradiction_mode_summary": {
            "negated_opposition_share": 0.1,
            "inhibited_opposition_share": 0.1,
        },
        "contradiction_coupling_active": True,
    }
    return {
        "04_dlcr_full.json": {
            "sessions": [{"session_id": session_id, "crossplane_contradiction_package": dict(cpkg)}]
        },
        "05_sealed_multiscale.json": {"sessions": [{"session_id": session_id}]},
        "06_product_analyze.json": {"sessions": [{"session_id": session_id, "extended": {"session_contradiction_mode": "conflict_bearing_interpretable"}}]},
        "09_session_topology.json": {"sessions": [{"session_id": session_id, "session_topology": {}}]},
        "20_main_engine_full_context.json": {
            "sessions": [{"session_id": session_id}],
            "crossplane_contradiction_by_session": {session_id: dict(cpkg)},
        },
    }


def test_valid_bundle_passes_contract_validation() -> None:
    from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract

    payloads = _session_payload()
    out = validate_contradiction_contract(payloads)
    assert out["contract_valid"] is True
    assert out["missing_required_fields"] == []
    assert out["authority_conflicts"] == []


def test_missing_canonical_field_fails_validation() -> None:
    from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract

    payloads = _session_payload()
    cpkg = payloads["04_dlcr_full.json"]["sessions"][0]["crossplane_contradiction_package"]
    cpkg.pop("effective_contradiction_load")
    payloads["20_main_engine_full_context.json"]["crossplane_contradiction_by_session"]["s1"].pop(
        "effective_contradiction_load"
    )
    out = validate_contradiction_contract(payloads)
    assert out["contract_valid"] is False
    assert any("effective_contradiction_load" in x for x in out["missing_required_fields"])


def test_deprecated_alias_is_flagged() -> None:
    from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract

    payloads = _session_payload()
    payloads["06_product_analyze.json"]["sessions"][0]["extended"]["semantic_conflict_score"] = 0.9
    out = validate_contradiction_contract(payloads)
    assert out["contract_valid"] is False
    assert any("semantic_conflict_score" in x for x in out["deprecated_fields_found"])


def test_conflicting_field_authority_is_flagged() -> None:
    from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract

    payloads = _session_payload()
    payloads["20_main_engine_full_context.json"]["crossplane_contradiction_by_session"]["s1"][
        "effective_contradiction_load"
    ] = 0.12
    out = validate_contradiction_contract(payloads)
    assert out["contract_valid"] is False
    assert out["authority_conflicts"]


def test_old_bundle_handled_gracefully() -> None:
    from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract

    payloads = {"04_dlcr_full.json": {"sessions": [{"session_id": "legacy"}]}}
    out = validate_contradiction_contract(payloads)
    assert out["contract_valid"] is False
    assert isinstance(out["compatibility_notes"], list)


def test_inspector_emits_contract_validation_fields(tmp_path) -> None:
    import json
    from tools.inspect_tfp_bundle_output import inspect_bundle

    d = tmp_path / "bundle_contract"
    d.mkdir()
    sid = "s_contract"
    payloads = _session_payload(sid)
    # make one required field missing to force contract failure in inspector output
    payloads["04_dlcr_full.json"]["sessions"][0]["crossplane_contradiction_package"].pop(
        "effective_contradiction_load"
    )
    payloads["20_main_engine_full_context.json"]["crossplane_contradiction_by_session"][sid].pop(
        "effective_contradiction_load"
    )
    for name in ("04_dlcr_full.json", "05_sealed_multiscale.json", "06_product_analyze.json", "09_session_topology.json", "20_main_engine_full_context.json"):
        (d / name).write_text(json.dumps(payloads[name]), encoding="utf-8")
    report = inspect_bundle(d)
    assert report["contradiction_contract_valid"] is False
    assert report["missing_required_contradiction_fields"]
    assert "contract_recommended_action" in report

