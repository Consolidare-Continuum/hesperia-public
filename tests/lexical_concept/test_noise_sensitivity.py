from core.diagnostics.noise_harness import run_noise_sensitivity
from core.engine.lexical_concept.pipeline import run_dlcr_pipeline


def test_noise_sensitivity_is_bounded() -> None:
    text = "The session has clear structure but unstable emotional transitions."
    report = run_noise_sensitivity(text, run_dlcr_pipeline)
    assert report["stable"] is True
    assert report["max_deviation"] <= 0.35

