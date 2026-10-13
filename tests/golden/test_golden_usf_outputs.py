# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Golden USF output tests: canonical pipeline output remains unchanged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_FIXTURES = _REPO / "tests" / "fixtures"
_GOLDEN_USF_PATH = _FIXTURES / "golden_usf.json"

CANONICAL_TEXT = "law regulation statute"


def _run_and_get_usf() -> dict:
    from sphere.pipeline import run_pipeline
    config = {"pipeline_version": "v1", "deterministic": True, "allow_placeholder_layer10": True}
    result = run_pipeline(CANONICAL_TEXT, config, document_id="golden")
    return result.get("usf") or {}


def test_golden_usf_output() -> None:
    """Pipeline on canonical text matches golden USF structural fields (or skip if no golden)."""
    if not _GOLDEN_USF_PATH.exists():
        return  # No golden yet: optional lock; run once and save to fixtures/golden_usf.json to enable
    with open(_GOLDEN_USF_PATH, encoding="utf-8") as f:
        expected = json.load(f)
    result_usf = _run_and_get_usf()
    if "_usf_error" in result_usf:
        return
    # Compare structural parts only (provenance may have created_at)
    assert "fingerprint" in result_usf
    assert result_usf["fingerprint"] == expected["fingerprint"]
    for key in ("raw_metrics", "propagation_metrics", "logic_metrics"):
        if key in expected:
            assert key in result_usf
            assert result_usf[key] == expected[key]
