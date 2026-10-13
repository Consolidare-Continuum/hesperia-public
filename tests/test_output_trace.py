# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from core.engine.output_trace import explain_metric


def test_explain_metric_governance_path() -> None:
    art = {
        "sessions": [
            {
                "result": {"governance": 0.37},
                "extended": {"total_tokens": 100, "matched_tokens": 100},
            }
        ]
    }
    t = explain_metric(art, "sessions[0].result.governance", verbose=True)
    assert t.get("value") == 0.37
    assert "source_layers" in t
    assert t.get("trace_sample", {}).get("total_tokens") == 100
