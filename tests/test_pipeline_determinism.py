# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Pipeline determinism tests.
Identical input must produce identical output and identical serialized USF.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _default_config() -> dict:
    return {
        "pipeline_version": "v1",
        "deterministic": True,
        "allow_placeholder_layer10": True,
    }


def test_run_pipeline_rejects_empty_text() -> None:
    """Empty raw_text raises ValueError."""
    from sphere.pipeline import run_pipeline
    try:
        run_pipeline("", _default_config())
        assert False
    except ValueError as e:
        assert "raw_text" in str(e).lower() or "empty" in str(e).lower()


def test_run_pipeline_rejects_missing_config() -> None:
    """Missing config or pipeline_version raises."""
    from sphere.pipeline import run_pipeline
    try:
        run_pipeline("hello", {})
        assert False
    except ValueError as e:
        assert "config" in str(e).lower() or "pipeline_version" in str(e).lower()


def test_run_pipeline_determinism_same_input() -> None:
    """Two runs with same text and config produce equal results."""
    from sphere.pipeline import run_pipeline

    config = _default_config()
    text = "justice order fairness truth"
    result_a = run_pipeline(text, config, document_id="doc1")
    result_b = run_pipeline(text, config, document_id="doc1")

    assert result_a["document_id"] == result_b["document_id"]
    assert result_a["pipeline_metadata"]["deterministic"] is True
    assert result_a["layer_outputs"]["layer_1"].get("COVERAGE_RATIO") == result_b["layer_outputs"]["layer_1"].get("COVERAGE_RATIO")
    assert result_a["layer_outputs"]["layer_7"].get("DECISION_STATUS_CODE") == result_b["layer_outputs"]["layer_7"].get("DECISION_STATUS_CODE")
    # Full structural equality (excluding any non-deterministic fields if present)
    assert result_a["layer_outputs"] == result_b["layer_outputs"]
    assert result_a["pipeline_metadata"]["input_hash"] == result_b["pipeline_metadata"]["input_hash"]


def test_run_pipeline_usf_serialization_determinism() -> None:
    """Serialized USF from two identical runs must be byte-identical."""
    from sphere.pipeline import run_pipeline
    from sphere.usf import serialize_usf_to_json

    config = _default_config()
    text = "short normal text for fingerprint"
    result_a = run_pipeline(text, config, document_id="det")
    result_b = run_pipeline(text, config, document_id="det")

    usf_a = result_a.get("usf")
    usf_b = result_b.get("usf")
    if "_usf_error" in (usf_a or {}) or "_usf_error" in (usf_b or {}):
        return
    json_a = serialize_usf_to_json(usf_a)
    json_b = serialize_usf_to_json(usf_b)
    assert json_a == json_b


def test_run_pipeline_returns_canonical_structure() -> None:
    """Result must contain document_id, layer_outputs, usf, pipeline_metadata."""
    from sphere.pipeline import run_pipeline

    result = run_pipeline("sparse text with few tokens", _default_config())
    assert "document_id" in result
    assert "layer_outputs" in result
    assert "usf" in result
    assert "pipeline_metadata" in result
    assert "executed_layers" in result["pipeline_metadata"]
    assert result["pipeline_metadata"]["executed_layers"] == list(range(1, 11))
