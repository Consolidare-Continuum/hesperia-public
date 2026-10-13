# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Fingerprint drift metric: formula and thresholds as in legacy/docs/refactor_notes/fingerprint_validation.md.
Consistent float precision (no rounding surprises).
"""

from __future__ import annotations

from typing import Any

# State keys used for state_delta (must match fingerprint shape)
FINGERPRINT_STATE_KEYS = (
    "structural_state",
    "dominant_area_id",
    "entropy_state",
    "tension_state",
    "propagation_state",
)
MINOR_CHANGE_THRESHOLD = 0.15
MAJOR_CHANGE_THRESHOLD = 0.40
DRIFT_PRECISION = 4  # decimal places for drift_score


def compute_drift_score(fp1: dict[str, Any], fp2: dict[str, Any]) -> float:
    """
    drift_score = (state_delta * 0.6) + (event_delta * 0.4)

    state_delta = changed_state_keys / total_state_keys
    event_delta = event_difference / total_events

    Returns value rounded to DRIFT_PRECISION for consistent float comparison.
    """
    total_state_keys = max(len(FINGERPRINT_STATE_KEYS), 1)
    changed = 0
    for k in FINGERPRINT_STATE_KEYS:
        v1 = fp1.get(k)
        v2 = fp2.get(k)
        if v1 != v2:
            changed += 1
    state_delta = changed / total_state_keys

    events1 = set(fp1.get("active_events") or [])
    events2 = set(fp2.get("active_events") or [])
    event_difference = len(events1 ^ events2)
    total_events = max(len(events1 | events2), 1)
    event_delta = event_difference / total_events

    score = (state_delta * 0.6) + (event_delta * 0.4)
    return round(float(score), DRIFT_PRECISION)
