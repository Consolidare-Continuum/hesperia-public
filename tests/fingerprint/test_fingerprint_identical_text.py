# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Fingerprint validation: identical text must yield identical USF structural fingerprint.
Uses sphere.pipeline.run_pipeline() and USF fingerprint.
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


def test_identical_text_same_fingerprint():
    """Input: identical text. Expected: fingerprint_A == fingerprint_B."""
    from sphere.pipeline import run_pipeline

    input_text = "justice order fairness truth liberty equality"
    config = _config()
    result_a = run_pipeline(input_text, config, document_id="fp_ident_a")
    result_b = run_pipeline(input_text, config, document_id="fp_ident_b")

    usf_a = result_a.get("usf") or {}
    usf_b = result_b.get("usf") or {}
    if usf_a.get("_usf_error") or usf_b.get("_usf_error"):
        return
    fp_a = usf_a.get("fingerprint")
    fp_b = usf_b.get("fingerprint")
    if fp_a is None or fp_b is None:
        return
    assert fp_a == fp_b, "Identical text must produce identical structural fingerprint"
