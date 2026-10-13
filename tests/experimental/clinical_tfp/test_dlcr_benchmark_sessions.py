# HESPERIA — RAD. Experimental DLCR checks on benchmark_sessions.yaml (Ethan INT-018/019).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[3]


def _load_benchmark_sessions() -> list[dict]:
    p = _REPO / "tests" / "experimental" / "clinical_tfp" / "benchmark_sessions.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return list(data.get("sessions") or [])


@pytest.mark.parametrize(
    "session_id",
    ["bench_001", "bench_002", "bench_003"],
)
def test_dlcr_pipeline_runs_on_benchmark_session(session_id: str) -> None:
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

    sessions = {str(s.get("session_id")): s for s in _load_benchmark_sessions()}
    assert session_id in sessions
    text = str(sessions[session_id].get("text") or "")
    assert text.strip()
    out = run_dlcr_pipeline(text, repo_root=_REPO)
    assert out.get("run") == "dlcr_pipeline_v1"
    assert isinstance(out.get("span_resolutions"), list)
    assert "lexical_hits_accepted" in out


def test_bench_001_dlcr_expected_bounds() -> None:
    """Optional expected.dlcr in benchmark_sessions.yaml (INT-019)."""
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

    sessions = {str(s.get("session_id")): s for s in _load_benchmark_sessions()}
    s = sessions["bench_001"]
    exp = (s.get("expected") or {}).get("dlcr") or {}
    if not exp:
        pytest.skip("no expected.dlcr on bench_001")
    text = str(s.get("text") or "")
    out = run_dlcr_pipeline(text, repo_root=_REPO)
    min_hits = int(exp.get("min_lexical_hits_accepted", 0))
    min_spans = int(exp.get("min_span_count", 0))
    assert int(out.get("lexical_hits_accepted") or 0) >= min_hits
    assert len(out.get("span_resolutions") or []) >= min_spans
