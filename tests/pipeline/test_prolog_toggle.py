# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline contract: prolog_logic shape when enable_prolog is False vs True.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _config(enable_prolog: bool = False):
    return {
        "pipeline_version": "v1",
        "deterministic": True,
        "enable_prolog": enable_prolog,
    }


def test_prolog_disabled_contract():
    """Case A: enable_prolog=False → prolog_logic = { derived_facts: [], rule_traces: [], prolog_diagnostics: {} } or iterations == 0."""
    from sphere.pipeline import run_pipeline

    result = run_pipeline("short text for contract", _config(False), document_id="no_prolog")
    assert "prolog_logic" in result
    pl = result["prolog_logic"]
    assert pl.get("derived_facts") == []
    assert pl.get("rule_traces") == []
    diag = pl.get("prolog_diagnostics")
    assert diag == {} or (isinstance(diag, dict) and diag.get("iterations", 0) == 0)


def test_prolog_enabled_contract():
    """Case B: enable_prolog=True → derived_facts is list, rule_traces is list, prolog_diagnostics['iterations'] >= 1."""
    from sphere.pipeline import run_pipeline

    result = run_pipeline(
        "justice order fairness truth",
        _config(True),
        document_id="with_prolog",
    )
    assert "prolog_logic" in result
    pl = result["prolog_logic"]
    assert isinstance(pl.get("derived_facts"), list)
    assert isinstance(pl.get("rule_traces"), list)
    diag = pl.get("prolog_diagnostics") or {}
    assert isinstance(diag, dict)
    assert diag.get("iterations", 0) >= 1


def test_backward_compatibility_baseline_config():
    """Baseline (enable_prolog=False, propagation_steps=1, damping default): no structural change; two runs identical."""
    from sphere.pipeline import run_pipeline

    config = {
        "pipeline_version": "v1",
        "deterministic": True,
        "enable_prolog": False,
    }
    # propagation_steps and damping_factor left at default (1 and 1.0)
    text = "justice order fairness truth"
    result1 = run_pipeline(text, config, document_id="base")
    result2 = run_pipeline(text, config, document_id="base")
    assert "document_id" in result1
    assert "layer_outputs" in result1
    assert "usf" in result1
    assert "prolog_logic" in result1
    assert result1["prolog_logic"]["derived_facts"] == []
    assert result1["prolog_logic"]["rule_traces"] == []
    assert result1["document_id"] == result2["document_id"]
    assert result1["pipeline_metadata"]["input_hash"] == result2["pipeline_metadata"]["input_hash"]
    # Determinism: same input → same output
    assert result1["usf"] == result2["usf"]
    assert result1["interpretation_metrics"] == result2["interpretation_metrics"]
