# HESPERIA — Bench-0 gold witness orchestrator. Copyright © 2026 igareosh.com.
"""Bench-0 (Colombo design, COLOMBO-HESPERIA-DEV-TEST-BENCH0-DESIGN-2026-07-26.md): the gold
reference core test for sealed Hesperia measurement under semantics-free Latin tokens.

Structural / math compliance only — schemas, shapes, finiteness, opaque-id pins, determinism.
Never reasons about what a letter "means"; never treats the flat a-z fallback as a bug (it is the
current sealed fallback signature, pinned as gold). Never touches core/, sphere/ internals, sealed
assets, or core/engine/module_aliases.py.

Exactly two HTTP calls per token supply everything Bench-0 needs — no extra pipeline passes:
- POST /analyze: L1 scalars, multiscale vectors, engine_result (FastAPI leg)
- POST /product/interpret (include_gap_report=True): ground_truth, gap_report,
  router_envelope.engine_trace (the same computation the hesperia-router MCP tool's backing
  function — sphere.router.tool_inquiry.build_tool_inquiry_packet — returns; MCP parity is
  therefore checked by comparing this field against /analyze's engine_result, not by invoking a
  live MCP process).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sphere.fpf_inspect.constants import CLIMB_ORDER
from sphere.fpf_inspect.probe import probe

from tools.hesperia_dev_test import gold, math_compliance
from tools.hesperia_dev_test.corpus import CorpusEntry, bench0_latin

_MCP_PARITY_FIELDS = ("trace_content_hash", "dominant_area_id", "dominant_family_id", "dominant_concept_id")


@dataclass
class Bench0Result:
    entry: CorpusEntry
    analyze_status: int | None = None
    interpret_status: int | None = None
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.analyze_status == 200 and self.interpret_status == 200 and not self.violations


def _dig_input_from_interpret(interpret_body: dict[str, Any]) -> dict[str, Any]:
    envelope = interpret_body.get("router_envelope") or {}
    engine = envelope.get("engine_trace") or {}
    dig_input = dict(engine)
    dig_input.setdefault("router_envelope", envelope)
    dig_input.setdefault("ground_truth", interpret_body.get("ground_truth") or {})
    return dig_input


def _check_inspect_slices(dig_input: dict[str, Any], gold_data: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    expected_schema = gold_data["inspect_slice_schema"]
    for layer_id in CLIMB_ORDER:
        slice_ = probe(layer_id, dig_input)
        if slice_.get("schema") != expected_schema:
            violations.append(f"{layer_id}: bad InspectSlice schema {slice_.get('schema')!r}")
        if slice_.get("engine_authored") is not True:
            violations.append(f"{layer_id}: engine_authored is not True")
        for key in ("logical", "weight", "source_activation", "fpf"):
            if key not in slice_:
                violations.append(f"{layer_id}: missing InspectSlice key {key!r}")
    return violations


def _check_mcp_parity(interpret_body: dict[str, Any], engine_result: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    mcp_engine_trace = (interpret_body.get("router_envelope") or {}).get("engine_trace") or {}
    for key in _MCP_PARITY_FIELDS:
        if mcp_engine_trace.get(key) != engine_result.get(key):
            violations.append(
                f"MCP/FastAPI parity mismatch on {key}: mcp={mcp_engine_trace.get(key)!r} "
                f"fastapi={engine_result.get(key)!r}"
            )
    return violations


def check_token(client: Any, entry: CorpusEntry, gold_data: dict[str, Any]) -> Bench0Result:
    result = Bench0Result(entry=entry)
    violations = result.violations

    analyze_resp = client.post("/analyze", json={"text": entry.token})
    result.analyze_status = analyze_resp.status_code
    if analyze_resp.status_code != 200:
        violations.append(f"/analyze status {analyze_resp.status_code}")
        return result
    analyze_body = analyze_resp.json()

    interpret_resp = client.post("/product/interpret", json={"text": entry.token, "include_gap_report": True})
    result.interpret_status = interpret_resp.status_code
    if interpret_resp.status_code != 200:
        violations.append(f"/product/interpret status {interpret_resp.status_code}")
        return result
    interpret_body = interpret_resp.json()

    # 4.4 FastAPI contract matrix
    violations.extend(math_compliance.check_analyze_contract(analyze_body))
    violations.extend(math_compliance.check_interpret_contract(interpret_body))

    # 4.3 math compliance: finiteness, vector lengths, L1 allowlist, activation ranges
    violations.extend(math_compliance.check_no_nan_inf(analyze_body))
    violations.extend(math_compliance.check_no_nan_inf(interpret_body))
    violations.extend(math_compliance.check_vector_lengths(analyze_body.get("multiscale_signals") or {}))
    violations.extend(math_compliance.check_l1_scalar_allowlist(analyze_body.get("L1") or {}))
    engine_result = analyze_body.get("engine_result") or {}
    violations.extend(math_compliance.check_activation_ranges(engine_result.get("trace") or []))

    # 4.2 gold pins (opaque-field equality only)
    violations.extend(gold.check_against_gold(analyze_body, interpret_body, gold_data))

    # 4.5 InspectSlice schema per layer (cheap; full dig timing stays in timing_probe.py soak)
    dig_input = _dig_input_from_interpret(interpret_body)
    violations.extend(_check_inspect_slices(dig_input, gold_data))

    # 4.6 MCP parity: router_envelope.engine_trace (MCP-backing call path) vs engine_result
    # (FastAPI /analyze call path) — both already fetched, no extra pipeline pass.
    violations.extend(_check_mcp_parity(interpret_body, engine_result))

    return result


def run_bench0(client: Any | None = None, corpus: list[CorpusEntry] | None = None) -> list[Bench0Result]:
    from tools.hesperia_dev_test.api_battery import in_process_client

    owns_client = client is None
    client = client or in_process_client()
    gold_data = gold.load_gold()
    try:
        return [check_token(client, entry, gold_data) for entry in (corpus or bench0_latin())]
    finally:
        if owns_client:
            close = getattr(client, "close", None)
            if callable(close):
                close()


def summarize(results: list[Bench0Result]) -> dict[str, Any]:
    failing = [r for r in results if not r.ok]
    return {
        "n_tokens": len(results),
        "n_ok": len(results) - len(failing),
        "n_failing": len(failing),
        "violations": {r.entry.token: r.violations for r in failing},
    }
