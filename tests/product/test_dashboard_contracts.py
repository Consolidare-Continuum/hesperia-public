from hesperia.product.dashboard_contracts import (
    DASHBOARD_SCHEMA_VERSION,
    build_dashboard_bundle,
    validate_dashboard_bundle,
)


def test_dashboard_bundle_validates() -> None:
    triz = {
        "contradictions": [],
        "innovation_clusters": [{"cluster_id": "c0", "innovation_score": 0.5, "concepts": ["a"]}],
        "narratives": [],
        "topology": {
            "family_hotspots": [{"area_a": 0, "family_a": 1, "area_b": 2, "family_b": 3, "hotspot_score": 0.4}],
            "strongest_paths": [{"path": [0, 1], "path_score": 0.3, "route_type": "local_route"}],
        },
    }
    b = build_dashboard_bundle(triz)
    assert b["schema_version"] == DASHBOARD_SCHEMA_VERSION
    assert validate_dashboard_bundle(b) == []
