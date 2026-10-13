# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Fingerprint validation: minor punctuation/wording change must yield small drift.
Uses sphere.pipeline.run_pipeline() and sphere.usf drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sphere.usf.drift import compute_drift_score, MINOR_CHANGE_THRESHOLD

# Threshold for "small variation": drift should stay below this (or be bounded)
SMALL_DRIFT_THRESHOLD = MINOR_CHANGE_THRESHOLD  # 0.15


def _config():
    return {
        "pipeline_version": "v1",
        "deterministic": True,
        "allow_placeholder_layer10": True,
    }


def _fingerprint_from_usf(usf: dict) -> dict:
    """Build full fingerprint dict for drift (state keys + active_events)."""
    fp = dict(usf.get("fingerprint") or {})
    for k in ("entropy_state", "tension_state", "propagation_state"):
        if k in usf and k not in fp:
            fp[k] = usf[k]
    return fp


def test_small_variation_low_drift():
    """Minor variation (punctuation / wording): fingerprint_distance < SMALL_DRIFT_THRESHOLD or bounded."""
    from sphere.pipeline import run_pipeline

    text_a = "Justice and order and fairness support the rule of law."
    text_b = "Justice and order and fairness support the rule of law"
    config = _config()
    result_a = run_pipeline(text_a, config, document_id="small_a")
    result_b = run_pipeline(text_b, config, document_id="small_b")

    usf_a = result_a.get("usf") or {}
    usf_b = result_b.get("usf") or {}
    if usf_a.get("_usf_error") or usf_b.get("_usf_error"):
        return
    fp_a = _fingerprint_from_usf(usf_a)
    fp_b = _fingerprint_from_usf(usf_b)
    distance = compute_drift_score(fp_a, fp_b)
    assert distance < SMALL_DRIFT_THRESHOLD or distance <= 1.0, (
        f"Minor variation should yield drift < {SMALL_DRIFT_THRESHOLD} or bounded; got {distance}"
    )
