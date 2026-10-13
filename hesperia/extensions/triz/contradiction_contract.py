"""TFP contradiction contract validator (v0.5.8 task10)."""

from __future__ import annotations

from typing import Any

CONTRADICTION_CONTRACT_SPEC_VERSION = "v0.5.8"

CANONICAL_CORE_FIELDS = (
    "raw_contradiction_load",
    "effective_contradiction_load",
    "contradiction_confidence_mean",
    "global_contradiction_load",
    "cross_area_contradiction_mass",
)

CANONICAL_STRUCTURAL_FIELDS = (
    "area_contradiction_pressure",
    "family_contradiction_pressure",
    "family_fragmentation_summary",
    "family_cross_area_bridge_mass",
    "family_intra_area_conflict_mass",
)

CANONICAL_DYNAMIC_FIELDS = (
    "segment_contradiction_loads",
    "transition_pressure",
    "activation_conflict_load",
    "latent_conflict_load",
)

CANONICAL_QUALIFICATION_FIELDS = (
    "uncertainty_adjusted_conflict_index",
    "lexical_semantic_conflict_split",
    "runtime_vs_calibration_conflict_split",
    "contradiction_mode_summary",
)

CANONICAL_PRODUCT_GOVERNANCE_FIELDS = (
    "conflict_integrity_score",
    "promotion_conflict_verdict",
    "release_conflict_gates",
    "conflict_release_summary",
)

FORBIDDEN_SYNONYM_FIELDS = (
    "conflict_score",
    "tension_score",
    "semantic_conflict_score",
    "conflict_pressure",
    "contradiction_pressure",
    "semantic_tension",
)


def _session_map(blob: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(blob, dict):
        return {}
    sessions = blob.get("sessions")
    if not isinstance(sessions, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in sessions:
        if isinstance(row, dict) and row.get("session_id") is not None:
            out[str(row["session_id"])] = row
    return out


def _flatten_keys(obj: Any, *, prefix: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.append(key)
            out.extend(_flatten_keys(v, prefix=key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            out.extend(_flatten_keys(v, prefix=key))
    return out


def _values_conflict(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) > 1e-6
    return a != b


def validate_contradiction_contract(bundle_payloads: dict[str, Any]) -> dict[str, Any]:
    """
    Validate contradiction contract conformance from loaded bundle artifacts.

    Expected keys in `bundle_payloads`:
    04_dlcr_full.json, 05_sealed_multiscale.json, 06_product_analyze.json,
    09_session_topology.json, 20_main_engine_full_context.json, 99_tfp_bundle_inspect.json (optional),
    CONSOLIDATION_MANIFEST.json (optional; 00_manifest.json accepted as consolidation manifest).
    """
    required_artifacts = (
        "04_dlcr_full.json",
        "05_sealed_multiscale.json",
        "06_product_analyze.json",
        "09_session_topology.json",
        "20_main_engine_full_context.json",
    )
    missing_required_artifacts = [name for name in required_artifacts if not isinstance(bundle_payloads.get(name), dict)]

    compatibility_notes: list[str] = []
    if "CONSOLIDATION_MANIFEST.json" not in bundle_payloads and "00_manifest.json" in bundle_payloads:
        compatibility_notes.append(
            "CONSOLIDATION_MANIFEST.json not present; using 00_manifest.json as consolidation manifest source."
        )

    deprecated_fields_found: list[str] = []
    for art_name, payload in bundle_payloads.items():
        if not isinstance(payload, dict):
            continue
        for dotted in _flatten_keys(payload):
            leaf = dotted.split(".")[-1]
            if leaf in FORBIDDEN_SYNONYM_FIELDS:
                deprecated_fields_found.append(f"{art_name}:{dotted}")

    d04 = bundle_payloads.get("04_dlcr_full.json")
    d06 = bundle_payloads.get("06_product_analyze.json")
    d20 = bundle_payloads.get("20_main_engine_full_context.json")

    m04 = _session_map(d04 if isinstance(d04, dict) else None)
    m06 = _session_map(d06 if isinstance(d06, dict) else None)

    cp20 = {}
    if isinstance(d20, dict) and isinstance(d20.get("crossplane_contradiction_by_session"), dict):
        cp20 = d20["crossplane_contradiction_by_session"]

    missing_required_fields: list[str] = []
    authority_conflicts: list[str] = []

    sids = sorted(set(m04) | set(cp20))
    for sid in sids:
        row04 = m04.get(sid) or {}
        cpkg = row04.get("crossplane_contradiction_package")
        cpkg = cpkg if isinstance(cpkg, dict) else {}
        cpkg20 = cp20.get(sid)
        cpkg20 = cpkg20 if isinstance(cpkg20, dict) else {}

        coupling_active = bool(cpkg.get("contradiction_coupling_active", cpkg20.get("contradiction_coupling_active", False)))
        required_now = coupling_active or bool(cpkg) or bool(cpkg20)
        if required_now:
            for f in CANONICAL_CORE_FIELDS + CANONICAL_STRUCTURAL_FIELDS + CANONICAL_DYNAMIC_FIELDS + CANONICAL_QUALIFICATION_FIELDS:
                if f not in cpkg and f not in cpkg20:
                    missing_required_fields.append(f"session={sid}:crossplane:{f}")

        # authoritative producer mismatch: 04 vs 20 for canonical core fields
        for f in CANONICAL_CORE_FIELDS:
            if f in cpkg and f in cpkg20 and _values_conflict(cpkg[f], cpkg20[f]):
                authority_conflicts.append(f"session={sid}:field={f}:04_dlcr_full.json!=20_main_engine_full_context.json")

        # product artifact must not claim canonical core authority
        row06 = m06.get(sid) or {}
        ext = row06.get("extended") if isinstance(row06.get("extended"), dict) else {}
        if isinstance(row06, dict):
            for f in CANONICAL_CORE_FIELDS:
                if f in row06 or (isinstance(ext, dict) and f in ext):
                    authority_conflicts.append(f"session={sid}:field={f}:06_product_analyze.json_claims_authority")

    inspector = bundle_payloads.get("99_tfp_bundle_inspect.json")
    if isinstance(inspector, dict):
        for f in CANONICAL_PRODUCT_GOVERNANCE_FIELDS:
            if f not in inspector:
                missing_required_fields.append(f"inspector:{f}")
    else:
        compatibility_notes.append("99_tfp_bundle_inspect.json missing; product/governance fields cannot be fully validated.")

    contract_valid = not (
        missing_required_artifacts or missing_required_fields or deprecated_fields_found or authority_conflicts
    )
    if missing_required_artifacts and not bundle_payloads:
        compatibility_notes.append("Legacy/partial bundle detected; contract check completed without parser crash.")

    return {
        "spec_version": CONTRADICTION_CONTRACT_SPEC_VERSION,
        "contract_valid": contract_valid,
        "missing_required_artifacts": missing_required_artifacts,
        "missing_required_fields": missing_required_fields,
        "deprecated_fields_found": deprecated_fields_found,
        "authority_conflicts": authority_conflicts,
        "compatibility_notes": compatibility_notes,
    }

