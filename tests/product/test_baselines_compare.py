from pathlib import Path

from research.evaluation.baselines.compare import run_triz_vs_baselines


def test_run_triz_vs_baselines_shape() -> None:
    d = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks" / "corpus_policy_polarized"
    out = run_triz_vs_baselines(d)
    assert "triz_layer" in out
    assert "keyword_baseline" in out
    assert "delta_summary" in out
