from core.engine.lexical_concept.pipeline import run_dlcr_pipeline


def test_run_is_deterministic_hash_stable() -> None:
    text = "Patient reports anxiety and asks for structure in dialogue."
    out1 = run_dlcr_pipeline(text)
    out2 = run_dlcr_pipeline(text)
    assert out1["deterministic_hash"] == out2["deterministic_hash"]

