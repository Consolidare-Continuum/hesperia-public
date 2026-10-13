# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA — Safeguard State Machine v0.1 (25_SPEC).
Logic-based structural stability: three consecutive logical failures → stop traversal.
Locked: CONSECUTIVE_FAIL_THRESHOLD=3, VALID_STREAK_RESET=2. No drift until Phase D or change control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Constants (DO NOT CHANGE per 25_SPEC §3)
CONSECUTIVE_FAIL_THRESHOLD = 3
VALID_STREAK_RESET = 2

# Hop summary: 1 = valid, 0 = invalid (logical failure)
HOP_VALID = 1
HOP_INVALID = 0


class TraversalStatus(Enum):
    OK = "OK"
    SAFEGUARD_STOP = "SAFEGUARD_STOP"


@dataclass
class SafeguardStopPayload:
    """Output when SAFEGUARD_STOP fires. Per 25_SPEC §6."""
    status: TraversalStatus = TraversalStatus.SAFEGUARD_STOP
    fail_count: int = 0
    fail_trace: list[Any] = field(default_factory=list)  # last 3 hop states
    obstacle_region: dict[str, Any] = field(default_factory=dict)  # LOGICAL_OBSTACLE_CLUSTER / UNSAFE


class TraversalSafeguard:
    """
    Per-traversal-context state machine. One instance per context (hex, family, or area cross-polarity).
    Per 25_SPEC §2, §4, §5, §6.
    """

    __slots__ = ("fail_count", "valid_streak", "_fail_trace", "_frozen", "_context_id")

    def __init__(self, context_id: str = ""):
        self.fail_count: int = 0
        self.valid_streak: int = 0
        self._fail_trace: list[Any] = []
        self._frozen: bool = False
        self._context_id: str = context_id or "default"

    def record_hop(self, hop_result: int, state_snapshot: Any = None) -> None:
        """
        Update state per 25_SPEC §4. hop_result: 1 = valid, 0 = invalid.
        If already frozen (SAFEGUARD_STOP), no-op.
        """
        if self._frozen:
            return
        if hop_result == HOP_VALID:
            self.valid_streak += 1
            if self.valid_streak >= VALID_STREAK_RESET:
                self.fail_count = 0
        else:
            self.fail_count += 1
            self.valid_streak = 0
            if state_snapshot is not None:
                self._fail_trace.append(state_snapshot)
                if len(self._fail_trace) > CONSECUTIVE_FAIL_THRESHOLD:
                    self._fail_trace.pop(0)

    def should_stop(self) -> bool:
        """True if fail_count >= CONSECUTIVE_FAIL_THRESHOLD (25_SPEC §5)."""
        return self.fail_count >= CONSECUTIVE_FAIL_THRESHOLD

    def safeguard_stop(self, region_key: str = "", hazard_value: Any = "UNSAFE") -> SafeguardStopPayload:
        """
        Freeze traversal; mark region LOGICAL_OBSTACLE_CLUSTER; return STOP payload (25_SPEC §6).
        Call after should_stop() is True. Idempotent once frozen.
        """
        self._frozen = True
        obstacle_region = {}
        if region_key:
            obstacle_region[region_key] = hazard_value
        # Last 3 states for diagnosis
        trace = list(self._fail_trace[-CONSECUTIVE_FAIL_THRESHOLD:]) if self._fail_trace else []
        return SafeguardStopPayload(
            status=TraversalStatus.SAFEGUARD_STOP,
            fail_count=self.fail_count,
            fail_trace=trace,
            obstacle_region=obstacle_region,
        )

    @property
    def is_frozen(self) -> bool:
        return self._frozen


def run_traversal_with_safeguard(
    hop_results: list[int],
    context_id: str = "",
    region_key: str = "",
) -> tuple[TraversalStatus, SafeguardStopPayload | None]:
    """
    Run a sequence of hop_results through one TraversalSafeguard. Returns (status, payload).
    payload is non-None only when status == SAFEGUARD_STOP.
    """
    guard = TraversalSafeguard(context_id=context_id)
    for i, hr in enumerate(hop_results):
        if guard.is_frozen:
            break
        guard.record_hop(hr, state_snapshot={"index": i, "hop_result": hr})
        if guard.should_stop():
            payload = guard.safeguard_stop(region_key=region_key or context_id)
            return (TraversalStatus.SAFEGUARD_STOP, payload)
    return (TraversalStatus.OK, None)
