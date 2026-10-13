# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA 25_SPEC — Safeguard State Machine stress tests.
Force safeguard to fire; valid_streak resets fail_count. Per GENA-HESPERIA-SAFEGUARD-STRESS-TEST-RESULTS.
"""

from __future__ import annotations

try:
    from core.propagation.safeguard_state_machine import (
        CONSECUTIVE_FAIL_THRESHOLD,
        VALID_STREAK_RESET,
        HOP_VALID,
        HOP_INVALID,
        TraversalSafeguard,
        TraversalStatus,
        SafeguardStopPayload,
        run_traversal_with_safeguard,
    )
except ImportError:
    from safeguard_state_machine import (
        CONSECUTIVE_FAIL_THRESHOLD,
        VALID_STREAK_RESET,
        HOP_VALID,
        HOP_INVALID,
        TraversalSafeguard,
        TraversalStatus,
        SafeguardStopPayload,
        run_traversal_with_safeguard,
    )


def test_three_failures_trigger_stop():
    """Three consecutive hop_result=0 → should_stop() True; safeguard_stop() returns SAFEGUARD_STOP, fail_count=3, obstacle_region set."""
    g = TraversalSafeguard(context_id="test")
    assert g.should_stop() is False
    g.record_hop(HOP_INVALID, {"step": 1})
    g.record_hop(HOP_INVALID, {"step": 2})
    assert g.should_stop() is False
    g.record_hop(HOP_INVALID, {"step": 3})
    assert g.should_stop() is True
    payload = g.safeguard_stop(region_key="hex_12")
    assert payload.status == TraversalStatus.SAFEGUARD_STOP
    assert payload.fail_count == 3
    assert "hex_12" in payload.obstacle_region
    assert payload.obstacle_region["hex_12"] == "UNSAFE"
    assert len(payload.fail_trace) <= 3
    assert g.is_frozen is True
    # Idempotent: further record_hop no-op
    g.record_hop(HOP_VALID)
    assert g.fail_count == 3


def test_valid_streak_resets_fail_count():
    """After 2 failures, two valid hops (valid_streak >= 2) reset fail_count to 0; one subsequent failure does not trigger stop."""
    g = TraversalSafeguard(context_id="test2")
    g.record_hop(HOP_INVALID)
    g.record_hop(HOP_INVALID)
    assert g.fail_count == 2
    assert g.valid_streak == 0
    g.record_hop(HOP_VALID)
    assert g.valid_streak == 1
    assert g.fail_count == 2  # not reset yet
    g.record_hop(HOP_VALID)
    assert g.valid_streak == 2
    assert g.fail_count == 0  # reset
    g.record_hop(HOP_INVALID)
    assert g.fail_count == 1
    assert g.should_stop() is False


def test_run_traversal_with_safeguard_ok():
    status, payload = run_traversal_with_safeguard([1, 1, 1, 1], context_id="c1")
    assert status == TraversalStatus.OK
    assert payload is None


def test_run_traversal_with_safeguard_stop():
    status, payload = run_traversal_with_safeguard([1, 0, 0, 0], context_id="c2", region_key="area_3")
    assert status == TraversalStatus.SAFEGUARD_STOP
    assert payload is not None
    assert payload.fail_count == 3
    assert "area_3" in payload.obstacle_region


def test_constants_locked():
    assert CONSECUTIVE_FAIL_THRESHOLD == 3
    assert VALID_STREAK_RESET == 2
