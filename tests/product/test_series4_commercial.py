# Series 4 — multicorpus, comparison, tenant, contracts, pricing

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hesperia.product.comparison_engine import compare_policy_reports, compare_reports_unified
from hesperia.product.multicorpus_runner import CorpusInput, run_corpus_batch
from hesperia.product.package_builder import PRODUCT_SKUS, build_policy_package
from hesperia.product.pricing_units import estimate_usage_units
from hesperia.product.tenant_context import TenantContext
from hesperia.product.tenant_guard import TenantIsolationViolation, assert_tenant_output_path
from hesperia.product.api_contracts.triz_analysis_v1 import wrap_triz_analyze_response
from hesperia.product.api_contracts.triz_export_v1 import wrap_triz_export_response


def test_multicorpus_batch(tmp_path: Path) -> None:
    bench = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks" / "corpus_policy_coherent"
    spec = json.loads((bench / "graph.json").read_text(encoding="utf-8"))
    tenant = TenantContext(tenant_id="t_batch", project_id="p1")
    r = run_corpus_batch(
        [CorpusInput(corpus_id="c1", active_graph=spec["active_graph"], topology=spec.get("topology"))],
        "policy_detector",
        batch_mode="single_corpus",
        tenant=tenant,
        output_root=tmp_path,
    )
    assert len(r.runs) == 1
    assert Path(r.runs[0].report_path).is_file()


def test_compare_policy() -> None:
    bench = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks"
    a = json.loads((bench / "corpus_policy_coherent" / "graph.json").read_text())
    b = json.loads((bench / "corpus_policy_polarized" / "graph.json").read_text())
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete

    ta = run_triz_analysis_complete(active_graph_from_payload(a["active_graph"]), a.get("topology"))
    tb = run_triz_analysis_complete(active_graph_from_payload(b["active_graph"]), b.get("topology"))
    ra = build_policy_package(ta, "A")["report"]
    rb = build_policy_package(tb, "B")["report"]
    d = compare_policy_reports(ra, rb)
    assert "tension_delta" in d
    c = compare_reports_unified("A", "B", PRODUCT_SKUS["policy_detector"], ra, rb, product_kind="policy")
    assert c.summary_text


def test_tenant_isolation_raises() -> None:
    t = TenantContext(tenant_id="acme", project_id="proj")
    with pytest.raises(TenantIsolationViolation):
        assert_tenant_output_path(Path("/tmp/wrong/acme_only"), t)


def test_api_wraps() -> None:
    bench = Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks" / "corpus_policy_polarized"
    spec = json.loads((bench / "graph.json").read_text(encoding="utf-8"))
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete

    triz = run_triz_analysis_complete(active_graph_from_payload(spec["active_graph"]), spec.get("topology"))
    w = wrap_triz_analyze_response("x", triz)
    assert w["api_version"] == "v1"
    pkg = build_policy_package(triz, "x")
    wrap_triz_export_response(pkg["sku"], {k: v for k, v in pkg.items() if k != "sku"})


def test_pricing_estimate() -> None:
    u = estimate_usage_units({"product_sku": "HSP-TRIZ-P1", "corpus_count": 3, "comparison_count": 0})
    assert u.estimated_units >= 1
    u2 = estimate_usage_units({"comparison_count": 2, "product_sku": "HSP-TRIZ-P1"})
    assert u2.billing_unit == "PER_COMPARISON"
