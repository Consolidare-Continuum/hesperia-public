import json
from pathlib import Path

from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from hesperia.product.package_builder import PRODUCT_SKUS, build_policy_package, package_to_json


def test_policy_package_complete() -> None:
    root = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks" / "corpus_policy_polarized"
    spec = json.loads((root / "graph.json").read_text(encoding="utf-8"))
    triz = run_triz_analysis_complete(
        active_graph_from_payload(spec["active_graph"]),
        spec.get("topology"),
    )
    pkg = build_policy_package(triz, "test_corpus")
    assert pkg["sku"] == PRODUCT_SKUS["policy_detector"]
    assert pkg["report"]["summary_text"]
    assert "exports" in pkg
    s = package_to_json(pkg)
    assert "HSP-TRIZ-P1" in s
