# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Pilot MVP acceptance checklist (programmatic)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from hesperia.extensions.triz.guards import TrizStructuralViolation, guard_no_meta_lexical_activation
from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from hesperia.product.api_contracts.triz_analysis_v1 import wrap_triz_analyze_response
from hesperia.product.api_contracts.triz_export_v1 import wrap_triz_export_response
from hesperia.product.comparison_engine import compare_reports_unified
from hesperia.product.package_builder import PRODUCT_SKUS, build_policy_package
from hesperia.product.release_gate import run_release_gate
from hesperia.product.tenant_context import TenantContext
from hesperia.product.tenant_guard import TenantIsolationViolation, assert_tenant_output_path


@dataclass
class MVPAcceptanceResult:
    passed: bool
    failed_checks: list[str] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    generated_artifacts: list[str] = field(default_factory=list)


def run_mvp_acceptance(
    *,
    benchmark_root: Path | None = None,
    tmp_output: Path | None = None,
) -> MVPAcceptanceResult:
    failed: list[str] = []
    passed: list[str] = []
    artifacts: list[str] = []
    root = Path(__file__).resolve().parents[2]
    bench = benchmark_root or root / "hesperia" / "extensions" / "triz" / "benchmarks"
    tmp = tmp_output or root / "outputs" / "_mvp_acceptance_test" / "proj1"

    # Functional: analyze end-to-end
    pol = bench / "corpus_policy_polarized"
    spec = json.loads((pol / "graph.json").read_text(encoding="utf-8"))
    triz = run_triz_analysis_complete(active_graph_from_payload(spec["active_graph"]), spec.get("topology"))
    try:
        wrap_triz_analyze_response("polarized", triz)
        passed.append("analyze_contract")
    except Exception as e:
        failed.append(f"analyze_contract:{e}")

    pkg = build_policy_package(triz, "polarized")
    if not pkg.get("report", {}).get("summary_text"):
        failed.append("product_summary_text")
    else:
        passed.append("product_summary_text")

    try:
        inner = {k: v for k, v in pkg.items() if k != "sku"}
        wrap_triz_export_response(pkg["sku"], inner)
        passed.append("export_bundle")
    except Exception as e:
        failed.append(f"export_bundle:{e}")

    # Compare two corpora
    coh = bench / "corpus_policy_coherent"
    sc = json.loads((coh / "graph.json").read_text(encoding="utf-8"))
    triz_b = run_triz_analysis_complete(active_graph_from_payload(sc["active_graph"]), sc.get("topology"))
    pa = build_policy_package(triz, "a")["report"]
    pb = build_policy_package(triz_b, "b")["report"]
    cmp = compare_reports_unified("a", "b", PRODUCT_SKUS["policy_detector"], pa, pb, product_kind="policy")
    if not cmp.summary_text:
        failed.append("comparison_summary")
    else:
        passed.append("compare_two_corpora")

    # Structural
    try:
        guard_no_meta_lexical_activation({"bad": 5})
        failed.append("meta_guard")
    except TrizStructuralViolation:
        passed.append("meta_guard")

    # Tenant isolation
    tenant = TenantContext(tenant_id="t_acme", project_id="p1")
    p = tmp / "run_x"
    try:
        assert_tenant_output_path(p, tenant)
        failed.append("tenant_path_wrong_tenant")
    except TenantIsolationViolation:
        pass
    good = root / "outputs" / "t_acme" / "p1" / "run_test"
    try:
        assert_tenant_output_path(good, tenant)
        passed.append("tenant_path_ok")
    except TenantIsolationViolation:
        failed.append("tenant_path_ok")

    # Gate
    g = run_release_gate(benchmark_root=bench, fit_threshold=0.1)
    if not g.passed:
        failed.append(f"readiness_gate:{g.failures[:2]}")
    else:
        passed.append("readiness_gate")

    ok = len(failed) == 0
    return MVPAcceptanceResult(passed=ok, failed_checks=failed, passed_checks=passed, generated_artifacts=artifacts)
