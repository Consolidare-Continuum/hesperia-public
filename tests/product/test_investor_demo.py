from hesperia.product.investor_demo import build_investor_snapshot


def test_investor_snapshot_keys() -> None:
    bundle = {
        "reports": {
            "contradiction_report": {
                "global_tension_index": 0.71,
                "top_conflict_families": [{"area_a": 0, "area_b": 2}],
            }
        }
    }
    s = build_investor_snapshot("corp1", bundle)
    assert s["product"] == "Policy Contradiction Detector"
    assert s["supporting_metrics"]["global_tension_score"] == 0.71
    assert "what_generic_methods_miss" in s
