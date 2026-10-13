# HESPERIA — FPF-BUII layer probes (read-only view of analyze_result).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any, Callable

from sphere.fpf_inspect.constants import (
    L6_LIVE_FIELDS,
    L6_STUB_FIELDS,
    PROVISIONAL_40_POLICY,
    PROVISIONAL_ANCHOR_MAP,
    PROVISIONAL_HEX_ROTATION_R0,
)
from sphere.fpf_inspect.fingerprint import engine_fingerprint, pin_matches_expected, resolve_fpf_pin
from sphere.fpf_inspect.schemas import make_gap, make_inspect_slice


def _layer_block(result: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        block = result.get(key)
        if isinstance(block, dict) and block:
            return block
    return {}


def probe_l0(analyze_result: dict[str, Any] | None) -> dict[str, Any]:
    missing: list[str] = []
    if not analyze_result:
        missing.append("analyze_result")
    pin = resolve_fpf_pin()
    if not pin_matches_expected(pin):
        missing.append("fpf_pin_mismatch")
    fp = engine_fingerprint(analyze_result)
    return make_inspect_slice(
        layer_id="L0",
        logical={"analyze_present": bool(analyze_result)},
        weight={"pipeline_deterministic": bool(
            (analyze_result or {}).get("pipeline_metadata", {}).get("deterministic")
        )},
        source_activation={
            "corpus_snapshot_id": (analyze_result or {}).get("document_id"),
            "engine_fingerprint": fp,
            "fpf_pin": pin,
        },
        evidence_ids=["analyze_fingerprint"] if analyze_result else [],
        missing_evidence=missing,
        logic={"facts": [{"pin_ok": pin_matches_expected(pin)}], "actions": []},
    )


def probe_l1(analyze_result: dict[str, Any]) -> dict[str, Any]:
    shadow = analyze_result.get("shadow_metrics") or {}
    vector = shadow.get("corrected_area_vector") or []
    missing: list[str] = []
    if not vector:
        missing.append("corrected_area_vector")
    return make_inspect_slice(
        layer_id="L1",
        logical={"shadow_present": bool(shadow)},
        weight={"area_vector_len": len(vector)},
        source_activation={"document_id": analyze_result.get("document_id")},
        evidence_ids=["shadow_area_vector"] if vector else [],
        missing_evidence=missing,
    )


def probe_l2(analyze_result: dict[str, Any]) -> dict[str, Any]:
    interp = analyze_result.get("interpretation_metrics") or {}
    missing: list[str] = []
    if not interp.get("structural_state"):
        missing.append("structural_state")
    return make_inspect_slice(
        layer_id="L2",
        logical={"structural_state": interp.get("structural_state")},
        weight={"dominance_strength": interp.get("dominance_strength")},
        source_activation={"dominant_area_id": interp.get("dominant_area_id")},
        evidence_ids=["structural_state"] if interp.get("structural_state") else [],
        missing_evidence=missing,
    )


def probe_l3(analyze_result: dict[str, Any]) -> dict[str, Any]:
    dyn = analyze_result.get("dynamism_metrics") or {}
    missing: list[str] = []
    if "stability_index" not in dyn:
        missing.append("stability_index")
    return make_inspect_slice(
        layer_id="L3",
        logical={"dynamism_present": bool(dyn)},
        weight={"stability_index": dyn.get("stability_index"), "curvature": dyn.get("curvature")},
        source_activation={"document_id": analyze_result.get("document_id")},
        evidence_ids=["stability_index"] if "stability_index" in dyn else [],
        missing_evidence=missing,
    )


def probe_l4(analyze_result: dict[str, Any]) -> dict[str, Any]:
    l4 = _layer_block(analyze_result, "layer_4", "l4_metrics")
    missing: list[str] = []
    evidence_ids: list[str] = []
    if not l4:
        missing.append("l4_metrics")
    else:
        for key in ("EVIDENCE_SUPPORT_SCORE", "RETRIEVAL_COVERAGE"):
            if key in l4:
                evidence_ids.append(key.lower())
        if not evidence_ids:
            # Present but no known live keys — coverage gap, not silent success.
            missing.append("l4_live_fields")
    return make_inspect_slice(
        layer_id="L4",
        logical={"l4_present": bool(l4)},
        weight={k: l4[k] for k in ("EVIDENCE_SUPPORT_SCORE",) if k in l4},
        source_activation={"retrieval_present": bool(l4)},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
    )


def probe_l5(analyze_result: dict[str, Any]) -> dict[str, Any]:
    l5 = _layer_block(analyze_result, "layer_5", "l5_metrics")
    missing: list[str] = []
    evidence_ids: list[str] = []
    gates: list[dict[str, Any]] = []
    if not l5:
        missing.append("l5_metrics")
    else:
        if "CONTRADICTION_PRESSURE_SCORE" in l5:
            evidence_ids.append("contradiction_pressure")
        else:
            missing.append("contradiction_pressure")
        gate_val = l5.get("REALITY_GATE_COUNTER_EVIDENCE")
        if gate_val is not None:
            evidence_ids.append("counter_evidence_gate")
            gates.append(
                {
                    "gate_id": "reality_gate_counter_evidence",
                    "decision": "PASS" if gate_val else "BLOCK",
                }
            )
    return make_inspect_slice(
        layer_id="L5",
        logical={"contradiction_pressure": l5.get("CONTRADICTION_PRESSURE_SCORE")},
        weight={"anti_region_size": l5.get("ANTI_REGION_SIZE")},
        source_activation={"l5_source": "core.layers.layer_5" if l5 else None},
        evidence_ids=evidence_ids,
        gates=gates,
        missing_evidence=missing,
    )


def probe_l6(analyze_result: dict[str, Any]) -> dict[str, Any]:
    """Live L6 fields only — stubs never become evidence_ids (SPEC §4 L6 / BUII-02)."""
    l6 = _layer_block(analyze_result, "layer_6", "l6_metrics", "dynamism_metrics")
    # Prefer explicit layer_6; if we fell through to dynamism_metrics, treat as no L6 layer block.
    explicit = _layer_block(analyze_result, "layer_6", "l6_metrics")
    missing: list[str] = []
    evidence_ids: list[str] = []
    unfit: list[str] = []
    if not explicit:
        missing.append("l6_metrics")
        return make_inspect_slice(
            layer_id="L6",
            absent_reason="l6_metrics_absent",
            missing_evidence=missing,
        )

    for key, val in explicit.items():
        if key in L6_STUB_FIELDS:
            unfit.append(key)
            continue
        if key in L6_LIVE_FIELDS:
            evidence_ids.append(f"l6_{key.lower()}")
    # Never list stubs as evidence — even if a caller stuffed them into a fake list.
    leaked = [e for e in evidence_ids if any(s.lower() in e for s in L6_STUB_FIELDS)]
    if leaked:
        missing.append("l6_stub_leak")

    return make_inspect_slice(
        layer_id="L6",
        logical={"live_field_count": len(evidence_ids), "stub_fields_seen": len(unfit)},
        weight={k: explicit[k] for k in L6_LIVE_FIELDS if k in explicit},
        source_activation={"l6_source": "core.layers.layer_6"},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
        logic={
            "facts": [{"unfit_stub_fields": sorted(unfit)[:21]}],
            "actions": [],
            "hard_rule": "L6 stubs never EvidencePrimitive",
        },
    )


def probe_l7(analyze_result: dict[str, Any]) -> dict[str, Any]:
    l7 = _layer_block(analyze_result, "layer_7", "l7_metrics")
    missing: list[str] = []
    evidence_ids: list[str] = []
    if not l7:
        missing.append("l7_metrics")
    else:
        for eid, key in (
            ("trust_tier", "TRUST_TIER"),
            ("system_confidence", "SYSTEM_CONFIDENCE_SCORE"),
            ("decision_status", "DECISION_STATUS_CODE"),
        ):
            if key in l7:
                evidence_ids.append(eid)
            else:
                missing.append(eid)
    return make_inspect_slice(
        layer_id="L7",
        logical={"trust_tier": l7.get("TRUST_TIER"), "decision_status": l7.get("DECISION_STATUS_CODE")},
        weight={"system_confidence": l7.get("SYSTEM_CONFIDENCE_SCORE")},
        source_activation={"l7_source": "core.layers.layer_7" if l7 else None},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
    )


def probe_l8(analyze_result: dict[str, Any]) -> dict[str, Any]:
    l8 = _layer_block(analyze_result, "layer_8", "l8_metrics")
    missing: list[str] = []
    if not l8:
        missing.append("l8_metrics")
    return make_inspect_slice(
        layer_id="L8",
        logical={"l8_present": bool(l8)},
        weight={"si_keys": sorted(l8.keys())[:12] if l8 else []},
        source_activation={"l8_source": "core.layers.layer_8" if l8 else None},
        evidence_ids=["l8_present"] if l8 else [],
        missing_evidence=missing,
        absent_reason=None if l8 else "l8_optional_in_mock",
    )


def probe_l9(analyze_result: dict[str, Any]) -> dict[str, Any]:
    logic_m = analyze_result.get("logic_metrics") or {}
    rules = logic_m.get("triggered_rules") or []
    missing: list[str] = []
    if not rules:
        missing.append("triggered_rules")
    evidence_ids = [f"rule_{r.get('type')}" for r in rules if isinstance(r, dict) and r.get("type")]
    return make_inspect_slice(
        layer_id="L9",
        logical={"triggered_rule_count": len(rules)},
        weight={"anomaly_flags": logic_m.get("anomaly_flags") or []},
        source_activation={"logic_source": "sphere.logic"},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
    )


def probe_gtp(analyze_result: dict[str, Any]) -> dict[str, Any]:
    gtp = analyze_result.get("gtp") or {}
    # Option B shipped (FPF-HSR-14) — hex_rotation_r0_interim cleared; keep 03/04 until freeze.
    provisional = [
        PROVISIONAL_40_POLICY,
        PROVISIONAL_ANCHOR_MAP,
    ]
    missing: list[str] = []
    evidence_ids: list[str] = []
    if not gtp:
        missing.append("gtp_block")
    else:
        evidence_ids.append("gtp_present")
        rot = gtp.get("hex_rotation")
        if rot is None and isinstance(gtp.get("thought_imprint"), dict):
            rot = gtp["thought_imprint"].get("hex_rotation")
        if rot is not None:
            evidence_ids.append("hex_rotation")
    return make_inspect_slice(
        layer_id="GTP",
        logical={
            "gtp_present": bool(gtp),
            "hex_rotation": (gtp.get("hex_rotation") if gtp else None),
            "hex_rotation_formula": "option_b_primary_side",
        },
        weight={"gtp_coherence": gtp.get("coherence") if gtp else None},
        source_activation={
            "gtp_current_hex": gtp.get("current_hex") if gtp else None,
        },
        evidence_ids=evidence_ids,
        missing_evidence=missing,
        provisional=provisional,
        logic={
            "facts": [
                {"adr": "FPF-HSR-02", "tag": "option_b_shipped"},
                {"adr": "FPF-HSR-03", "tag": PROVISIONAL_40_POLICY},
                {"adr": "FPF-HSR-04", "tag": PROVISIONAL_ANCHOR_MAP},
            ],
            "actions": [],
        },
    )


def probe_guards(analyze_result: dict[str, Any]) -> dict[str, Any]:
    guards = analyze_result.get("guards") or {}
    missing: list[str] = []
    evidence_ids: list[str] = []
    for name in ("sigma", "gamma", "theta"):
        if name not in guards:
            missing.append(f"guard_{name}")
        else:
            evidence_ids.append(f"guard_{name}")
    return make_inspect_slice(
        layer_id="Guards",
        logical={"guards_present": bool(guards)},
        weight={
            "sigma_passed": (guards.get("sigma") or {}).get("passed"),
            "gamma_passed": (guards.get("gamma") or {}).get("passed"),
            "theta_status": (guards.get("theta") or {}).get("status"),
        },
        source_activation={"guard_source": "sphere.guards"},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
    )


def probe_router(analyze_result: dict[str, Any]) -> dict[str, Any]:
    """FPF-MWI-10: envelope / ground_truth visibility in climb (read-only)."""
    envelope = analyze_result.get("router_envelope") or analyze_result.get("envelope") or {}
    gt = analyze_result.get("ground_truth") or {}
    missing: list[str] = []
    evidence_ids: list[str] = []
    if not envelope and not gt:
        missing.append("router_envelope_or_ground_truth")
    else:
        if envelope:
            evidence_ids.append("router_envelope")
        for name in ("logical", "weight", "source_activation"):
            if name in gt:
                evidence_ids.append(f"ground_truth_{name}")
            elif gt:
                missing.append(f"ground_truth_{name}")
    return make_inspect_slice(
        layer_id="Router",
        logical={"envelope_present": bool(envelope), "ground_truth_present": bool(gt)},
        weight={"ground_truth_keys": sorted(gt.keys()) if gt else []},
        source_activation={"router_fingerprint": envelope.get("router_fingerprint") if envelope else None},
        evidence_ids=evidence_ids,
        missing_evidence=missing,
    )


_PROBES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "L0": lambda r: probe_l0(r),
    "L1": probe_l1,
    "L2": probe_l2,
    "L3": probe_l3,
    "L4": probe_l4,
    "L5": probe_l5,
    "L6": probe_l6,
    "L7": probe_l7,
    "L8": probe_l8,
    "L9": probe_l9,
    "GTP": probe_gtp,
    "Guards": probe_guards,
    "Router": probe_router,
}


def probe(layer_id: str, analyze_result: dict[str, Any] | None) -> dict[str, Any]:
    """Probe one layer. L0 accepts None; other layers require a dict (empty ok)."""
    if layer_id not in _PROBES:
        raise ValueError(f"unknown layer_id: {layer_id}; known={sorted(_PROBES)}")
    if layer_id == "L0":
        return probe_l0(analyze_result)
    return _PROBES[layer_id](analyze_result or {})


def gaps_from_slice(slice_: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert InspectSlice missing_evidence + provisional into GapReport entries."""
    gaps: list[dict[str, Any]] = []
    layer_id = str(slice_.get("layer_id"))
    for mid in (slice_.get("fpf") or {}).get("missing_evidence") or []:
        gaps.append(
            make_gap(
                gap_id=f"gap.{layer_id.lower()}.{mid}",
                layer_id=layer_id,
                kind="missing_evidence",
                evidence_ids=[],
                advice_hint=f"Missing {mid} at {layer_id}",
            )
        )
    for tag in slice_.get("provisional") or []:
        adr = {
            PROVISIONAL_HEX_ROTATION_R0: "FPF-HSR-02",
            PROVISIONAL_40_POLICY: "FPF-HSR-03",
            PROVISIONAL_ANCHOR_MAP: "FPF-HSR-04",
        }.get(tag)
        gaps.append(
            make_gap(
                gap_id=f"gap.{tag}",
                layer_id=layer_id,
                kind="provisional_adr",
                adr_ref=adr,
                advice_hint=f"Provisional ADR tag {tag}",
            )
        )
    # L6 stub leak = unfit_exposure
    if layer_id == "L6" and "l6_stub_leak" in ((slice_.get("fpf") or {}).get("missing_evidence") or []):
        gaps.append(
            make_gap(
                gap_id="gap.l6.stub_as_evidence",
                layer_id="L6",
                kind="unfit_exposure",
                advice_hint="L6 stub field appeared as EvidencePrimitive — forbidden",
            )
        )
    return gaps
