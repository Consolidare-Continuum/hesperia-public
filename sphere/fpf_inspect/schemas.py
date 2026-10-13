# HESPERIA — FPF-BUII InspectSlice + GapReport builders.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any

from sphere.fpf_inspect.constants import GAP_REPORT_SCHEMA, INSPECT_SLICE_SCHEMA
from sphere.fpf_inspect.fingerprint import engine_fingerprint, resolve_fpf_pin, stable_json_hash


def make_inspect_slice(
    *,
    layer_id: str,
    logical: dict[str, Any] | None = None,
    weight: dict[str, Any] | None = None,
    source_activation: dict[str, Any] | None = None,
    absent_reason: str | None = None,
    evidence_ids: list[str] | None = None,
    gates: list[dict[str, Any]] | None = None,
    transitions: list[dict[str, Any]] | None = None,
    logic: dict[str, Any] | None = None,
    missing_evidence: list[str] | None = None,
    provisional: list[str] | None = None,
) -> dict[str, Any]:
    """Build one InspectSlice (SPEC §5.1) — engine_authored always True."""
    logical = dict(logical or {})
    weight = dict(weight or {})
    source_activation = dict(source_activation or {})
    if absent_reason and not (logical or weight or source_activation):
        # Layer truly has none of the three blocks — record why (still present as keys).
        logical = {"absent_reason": absent_reason}
        weight = {"absent_reason": absent_reason}
        source_activation = {"absent_reason": absent_reason}

    fpf = {
        "evidence_ids": list(evidence_ids or []),
        "gates": list(gates or []),
        "transitions": list(transitions or []),
        "logic": dict(logic or {}),
        "missing_evidence": list(missing_evidence or []),
    }
    body = {
        "schema": INSPECT_SLICE_SCHEMA,
        "layer_id": layer_id,
        "engine_authored": True,
        "logical": logical,
        "weight": weight,
        "source_activation": source_activation,
        "fpf": fpf,
        "provisional": list(provisional or []),
    }
    body["fingerprint"] = stable_json_hash(
        {k: body[k] for k in ("layer_id", "logical", "weight", "source_activation", "fpf", "provisional")}
    )
    return body


def make_gap_report(
    *,
    gaps: list[dict[str, Any]],
    analyze_result: dict[str, Any] | None,
    lowest_failed_layer: str | None = None,
) -> dict[str, Any]:
    """GapReport v0.1 (SPEC §5.2)."""
    if lowest_failed_layer is None:
        if gaps:
            # First gap in climb order among named layers; else first gap's layer.
            lowest_failed_layer = str(gaps[0].get("layer_id") or "unknown")
        else:
            lowest_failed_layer = "none"
    return {
        "schema": GAP_REPORT_SCHEMA,
        "lowest_failed_layer": lowest_failed_layer,
        "gaps": list(gaps),
        "engine_fingerprint": engine_fingerprint(analyze_result),
        "fpf_pin": resolve_fpf_pin(),
    }


def make_gap(
    *,
    gap_id: str,
    layer_id: str,
    kind: str,
    evidence_ids: list[str] | None = None,
    adr_ref: str | None = None,
    advice_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "id": gap_id,
        "layer_id": layer_id,
        "kind": kind,
        "evidence_ids": list(evidence_ids or []),
        "adr_ref": adr_ref,
        "advice_hint": advice_hint,
    }
