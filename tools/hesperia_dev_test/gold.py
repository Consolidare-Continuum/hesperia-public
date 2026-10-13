# HESPERIA — hesperia-dev-test Bench-0 gold loader. Copyright © 2026 igareosh.com.
"""Loads the pinned Bench-0 gold artifact (gold/bench0_v0_3.json) and compares live /analyze +
/product/interpret responses against it. Read-only: this module never writes the gold file.
Re-gold is an explicit Felix/Ethan step (see the artifact's own `re_gold_procedure` field), never
a silent overwrite here or in CI. v0_1/v0_2 kept in gold/ for history — re-golded to v0_3
2026-09-17 (operator igareosh explicit instruction, Felix acting Ethan-ratified per CSP;
system_version 0.7.1 -> 0.7.2 seal; every other pinned field verified unchanged empirically and
corroborated against the live production service, see bench0_v0_3.json's generated_by note).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GOLD_PATH = Path(__file__).resolve().parent / "gold" / "bench0_v0_3.json"


def load_gold() -> dict[str, Any]:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def check_against_gold(
    analyze_body: dict[str, Any],
    interpret_body: dict[str, Any],
    gold_data: dict[str, Any],
) -> list[str]:
    """Opaque-field equality only — never asserts what a value *means*, only that it still
    matches the pinned witness (ADV-09)."""
    violations: list[str] = []
    pins = gold_data["pins"]

    if analyze_body.get("system_version") != pins["system_version"]:
        violations.append(
            f"system_version drifted: {analyze_body.get('system_version')!r} != gold {pins['system_version']!r}"
        )

    l1 = analyze_body.get("L1") or {}
    if l1.get("CANONICAL_PIPELINE") != pins["canonical_pipeline"]:
        violations.append(f"CANONICAL_PIPELINE drifted: {l1.get('CANONICAL_PIPELINE')!r}")
    if l1.get("CALIBRATION_FALLBACK_USED") != pins["calibration_fallback_used"]:
        violations.append(f"CALIBRATION_FALLBACK_USED drifted: {l1.get('CALIBRATION_FALLBACK_USED')!r}")

    engine_result = analyze_body.get("engine_result") or {}
    for field_name in ("trace_content_hash", "dominant_area_id", "dominant_family_id", "dominant_concept_id"):
        if engine_result.get(field_name) != pins[field_name]:
            violations.append(
                f"{field_name} drifted: {engine_result.get(field_name)!r} != gold {pins[field_name]!r}"
            )

    trace_len = len(engine_result.get("trace") or [])
    if trace_len != pins["trace_len"]:
        violations.append(f"trace_len drifted: {trace_len} != gold {pins['trace_len']}")

    gt = interpret_body.get("ground_truth") or {}
    if gt.get("schema") != pins["ground_truth_schema"]:
        violations.append(f"ground_truth schema drifted: {gt.get('schema')!r} != gold {pins['ground_truth_schema']!r}")

    envelope = interpret_body.get("router_envelope") or {}
    if envelope.get("schema") != pins["router_envelope_schema"]:
        violations.append(
            f"router_envelope schema drifted: {envelope.get('schema')!r} != gold {pins['router_envelope_schema']!r}"
        )

    if interpret_body.get("schema") != pins["product_interpret_schema"]:
        violations.append(
            f"product_interpret schema drifted: {interpret_body.get('schema')!r} != gold {pins['product_interpret_schema']!r}"
        )

    gap_ids = sorted(g.get("id") for g in (interpret_body.get("gap_report") or {}).get("gaps") or [])
    if gap_ids != gold_data["gap_ids"]:
        violations.append(f"gap id set drifted: {gap_ids} != gold {gold_data['gap_ids']}")

    return violations
