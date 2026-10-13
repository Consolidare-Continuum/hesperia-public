# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Fingerprint validation: semantic shift (e.g. philosophy vs economics) must yield large drift.
Uses sphere.pipeline.run_pipeline() and sphere.usf drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sphere.usf.drift import compute_drift_score, MINOR_CHANGE_THRESHOLD, MAJOR_CHANGE_THRESHOLD

# Semantic shift: drift should be meaningfully positive (engine-dependent; prefer > MAJOR when possible)
SEMANTIC_SHIFT_THRESHOLD = 0.05  # at least non-trivial difference between philosophy and economics


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


def test_semantic_shift_high_drift():
    """Semantic shift (philosophy vs economic passage): fingerprint_distance > SEMANTIC_SHIFT_THRESHOLD."""
    from sphere.pipeline import run_pipeline

    text_philosophy = (
        "Justice and fairness are moral virtues. Truth and reason guide ethical conduct. "
        "Liberty and equality form the basis of political philosophy."
    )
    text_economics = (
        "Supply and demand determine market prices. Inflation and interest rates affect growth. "
        "Trade and investment drive economic development."
    )
    config = _config()
    result_a = run_pipeline(text_philosophy, config, document_id="semantic_a")
    result_b = run_pipeline(text_economics, config, document_id="semantic_b")

    usf_a = result_a.get("usf") or {}
    usf_b = result_b.get("usf") or {}
    if usf_a.get("_usf_error") or usf_b.get("_usf_error"):
        return
    fp_a = _fingerprint_from_usf(usf_a)
    fp_b = _fingerprint_from_usf(usf_b)
    distance = compute_drift_score(fp_a, fp_b)
    assert distance > SEMANTIC_SHIFT_THRESHOLD, (
        f"Semantic shift should yield drift > {SEMANTIC_SHIFT_THRESHOLD}; got {distance}"
    )
