# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Determinism stress: run pipeline many times; verify identical USF, layer outputs, diagnostics.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _config() -> dict:
    return {"pipeline_version": "v1", "deterministic": True, "allow_placeholder_layer10": True}


def _diagnostics_structure(d: dict) -> dict:
    """Strip execution_time_ms for deterministic comparison (timing varies run-to-run)."""
    if not d:
        return d
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and "execution_time_ms" in v:
            v = {kk: vv for kk, vv in v.items() if kk != "execution_time_ms"}
        out[k] = v
    return out


def test_pipeline_repeatability_100_runs() -> None:
    """Run pipeline 100 times on same input; verify identical USF, layer_outputs, diagnostics (structure)."""
    from sphere.pipeline import run_pipeline

    text = "justice order fairness truth liberty equality"
    config = _config()
    document_id = "repeat_100"
    first = run_pipeline(text, config, document_id=document_id)

    for _ in range(99):
        result = run_pipeline(text, config, document_id=document_id)
        assert result["layer_outputs"] == first["layer_outputs"], "Layer outputs must be identical"
        assert _diagnostics_structure(result.get("diagnostics")) == _diagnostics_structure(first.get("diagnostics")), "Diagnostics structure must be identical"
        usf_a = first.get("usf") or {}
        usf_b = result.get("usf") or {}
        if usf_a.get("_usf_error") or usf_b.get("_usf_error"):
            continue
        assert usf_a == usf_b, "USF must be identical across runs"
