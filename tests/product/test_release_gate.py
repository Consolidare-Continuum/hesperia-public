from pathlib import Path

from hesperia.product.release_gate import run_release_gate


def test_release_gate_passes_on_benchmarks() -> None:
    root = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks"
    g = run_release_gate(benchmark_root=root, fit_threshold=0.1)
    assert g.passed, g.failures
