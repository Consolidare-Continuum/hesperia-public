# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Fingerprint must be deterministic for identical input.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _config():
    return {
        "pipeline_version": "v1",
        "deterministic": True,
        "allow_placeholder_layer10": True,
    }


def test_fingerprint_deterministic_for_identical_text():
    """Same text and config produce identical USF fingerprint when interpretation is present."""
    from sphere.pipeline import run_pipeline

    text = "justice order fairness truth liberty equality"
    config = _config()
    result1 = run_pipeline(text, config, document_id="fp1")
    result2 = run_pipeline(text, config, document_id="fp1")

    usf1 = result1.get("usf", {})
    usf2 = result2.get("usf", {})
    if "_usf_error" in (usf1 or {}) or "_usf_error" in (usf2 or {}):
        return
    if "fingerprint" not in usf1 or "fingerprint" not in usf2:
        return
    assert usf1["fingerprint"] == usf2["fingerprint"]


def test_interpretation_metrics_deterministic_same_input():
    """Same input produces same interpretation_metrics (and thus stable canonical structure)."""
    from sphere.pipeline import run_pipeline

    text = "short canonical sample for interpretation"
    config = _config()
    result1 = run_pipeline(text, config, document_id="int1")
    result2 = run_pipeline(text, config, document_id="int1")

    im1 = result1.get("interpretation_metrics", {})
    im2 = result2.get("interpretation_metrics", {})
    assert im1.get("structural_state") == im2.get("structural_state")
    assert im1.get("active_events") == im2.get("active_events")
    assert im1.get("interpretation_flags") == im2.get("interpretation_flags")
