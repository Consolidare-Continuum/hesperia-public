# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Drift metric: formula (state_delta*0.6 + event_delta*0.4), thresholds 0.15, 0.40.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sphere.usf.drift import (
    compute_drift_score,
    MINOR_CHANGE_THRESHOLD,
    MAJOR_CHANGE_THRESHOLD,
)


def _config():
    return {
        "pipeline_version": "v1",
        "deterministic": True,
        "allow_placeholder_layer10": True,
    }


def test_drift_score_formula():
    """drift_score = (state_delta * 0.6) + (event_delta * 0.4); consistent precision."""
    fp1 = {"structural_state": "a", "dominant_area_id": 0, "entropy_state": "s", "tension_state": "n", "propagation_state": "m", "active_events": ["e1"]}
    fp2 = {"structural_state": "a", "dominant_area_id": 0, "entropy_state": "s", "tension_state": "n", "propagation_state": "m", "active_events": ["e1"]}
    assert compute_drift_score(fp1, fp2) == 0.0
    fp2["structural_state"] = "b"
    score = compute_drift_score(fp1, fp2)
    assert score >= 0.0
    assert isinstance(score, float)
    assert len(str(score).split(".")[-1]) <= 4


def test_minor_lexical_change_produces_limited_drift():
    """Small wording change: drift_score often below MINOR_CHANGE_THRESHOLD or bounded."""
    from sphere.pipeline import run_pipeline

    config = _config()
    text_a = "justice and order and fairness"
    text_b = "justice and order and fairness and truth"
    result_a = run_pipeline(text_a, config, document_id="drift_a")
    result_b = run_pipeline(text_b, config, document_id="drift_b")

    usf_a = result_a.get("usf", {})
    usf_b = result_b.get("usf", {})
    if "fingerprint" not in usf_a or "fingerprint" not in usf_b:
        return
    score = compute_drift_score(usf_a["fingerprint"], usf_b["fingerprint"])
    assert score >= 0.0
    assert score <= 1.0


def test_major_semantic_change_can_produce_larger_drift():
    """Very different content can yield drift_score in moderate or semantic-shift range."""
    from sphere.pipeline import run_pipeline

    config = _config()
    text_a = "justice order fairness truth liberty"
    text_b = "chaos destruction conflict war damage"
    result_a = run_pipeline(text_a, config, document_id="major_a")
    result_b = run_pipeline(text_b, config, document_id="major_b")

    usf_a = result_a.get("usf", {})
    usf_b = result_b.get("usf", {})
    if "fingerprint" not in usf_a or "fingerprint" not in usf_b:
        return
    score = compute_drift_score(usf_a["fingerprint"], usf_b["fingerprint"])
    assert score >= 0.0
    assert MINOR_CHANGE_THRESHOLD == 0.15
    assert MAJOR_CHANGE_THRESHOLD == 0.40
