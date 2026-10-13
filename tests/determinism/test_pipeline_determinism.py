# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline determinism: identical input produces identical output.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _config() -> dict:
    return {"pipeline_version": "v1", "deterministic": True, "allow_placeholder_layer10": True}


def test_pipeline_deterministic() -> None:
    """Same text and config yield identical pipeline result."""
    from sphere.pipeline import run_pipeline
    text = "law regulation statute"
    config = _config()
    result1 = run_pipeline(text, config, document_id="det")
    result2 = run_pipeline(text, config, document_id="det")
    assert result1["layer_outputs"] == result2["layer_outputs"]
    assert result1["pipeline_metadata"]["input_hash"] == result2["pipeline_metadata"]["input_hash"]
