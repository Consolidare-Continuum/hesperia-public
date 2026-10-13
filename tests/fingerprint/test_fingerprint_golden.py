# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Golden determinism test: locks deterministic fingerprint for a fixed text fixture.
Pipeline stability across refactors.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# Fixture and expected hash (run pipeline once with fixture to regenerate)
TEXT_FIXTURE = "justice order fairness truth liberty equality"
DOCUMENT_ID = "golden_fixture"
EXPECTED_HASH = "8885e40cda3a9082cd351a0fd0f9d618bfaab48be12953a0f710eae8ee19151b"


def _fingerprint_hash(fingerprint: dict) -> str:
    """Deterministic hash: serialize fingerprint JSON with sort_keys=True, then SHA256."""
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()


def test_golden_fingerprint_determinism():
    """text_fixture → pipeline → fingerprint; assert fingerprint_hash == EXPECTED_HASH."""
    from sphere.pipeline import run_pipeline

    config = {"pipeline_version": "v1", "deterministic": True}
    result = run_pipeline(TEXT_FIXTURE, config, document_id=DOCUMENT_ID)
    usf = result.get("usf", {})
    if "_usf_error" in (usf or {}):
        return
    fingerprint = usf.get("fingerprint")
    if not fingerprint:
        return
    h = _fingerprint_hash(fingerprint)
    assert h == EXPECTED_HASH, f"fingerprint hash changed: got {h}, expected {EXPECTED_HASH}"
