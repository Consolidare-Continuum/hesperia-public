# FPF-MWI-02 / PRE07-02/03 — gold E2E: GapReport + ground_truth three blocks.

from __future__ import annotations

import json

from sphere.fpf_inspect.climb import gap_detect
from sphere.fpf_inspect.map_hesperia_ops import build_hesperia_ops_map, ops_map_step
from sphere.router.tool_inquiry import build_tool_inquiry_packet

_TEXT = "FPF gold E2E synthetic text that includes with overlapping sides."


def test_gold_inquire_ground_truth_three_blocks() -> None:
    pkt = build_tool_inquiry_packet(_TEXT)
    gt = pkt["ground_truth"]
    assert set(gt) >= {"logical", "weight", "source_activation"}
    assert pkt["router_envelope"]["router_fingerprint"]


def test_gold_dig_gap_report_from_engine_trace() -> None:
    pkt = build_tool_inquiry_packet(_TEXT)
    engine = dict(pkt["router_envelope"].get("engine_trace") or {})
    engine["router_envelope"] = pkt["router_envelope"]
    engine["ground_truth"] = pkt["ground_truth"]
    a = gap_detect(engine)
    b = gap_detect(engine)
    assert a["schema"] == "hesperia.fpf_gap_report.v0_1"
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_hesperia_ops_map_builds_and_steps() -> None:
    sm = build_hesperia_ops_map()
    assert sm is not None
    out = ops_map_step(current_state="start", current_evidence="runtime_ok")
    assert "kind" in out
    assert out["map_id"] == "hesperia_ops"
