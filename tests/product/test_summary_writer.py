from hesperia.product.schemas.policy_detector_schema import PolicyDetectorReport
from hesperia.product.summary_writer import write_policy_summary


def test_policy_summary_three_modes() -> None:
    r = PolicyDetectorReport(
        corpus_id="x",
        generated_at="t",
        global_tension_score=0.71,
        top_conflict_clusters=[{"family_a": "fiscal", "family_b": "social"}],
        top_cross_domain_conflicts=[],
        dominant_triz_patterns=[{"triz_class": "segmentation"}],
    )
    a = write_policy_summary(r, "technical")
    b = write_policy_summary(r, "executive")
    c = write_policy_summary(r, "media")
    assert "0.71" in a and "0.71" in b and "0.71" in c
    assert a != b or "TRIZ" in a
