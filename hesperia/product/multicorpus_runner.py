# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Multi-corpus batch execution: single, time-series, cross-compare, benchmark pack."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from hesperia.product.package_builder import PRODUCT_SKUS, build_innovation_package, build_narrative_package, build_policy_package
from hesperia.product.tenant_context import TenantContext, validate_tenant_context
from hesperia.product.tenant_guard import assert_tenant_output_path

BatchMode = Literal["single_corpus", "time_series_corpus", "cross_corpus_compare", "benchmark_pack"]
ProductMode = Literal["policy_detector", "innovation_radar", "narrative_monitor"]


def load_benchmark_pack_inputs(benchmark_root: Path | str) -> list[CorpusInput]:
    """Expand hesperia/extensions/triz/benchmarks manifest into CorpusInput list (read-only)."""
    root = Path(benchmark_root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    out: list[CorpusInput] = []
    for b in manifest.get("benchmarks", []):
        sub = root / b.get("corpus_dir", "")
        spec = json.loads((sub / "graph.json").read_text(encoding="utf-8"))
        out.append(
            CorpusInput(
                corpus_id=str(b.get("id", sub.name)),
                active_graph=spec["active_graph"],
                topology=spec.get("topology"),
            )
        )
    return out


@dataclass
class CorpusInput:
    corpus_id: str
    active_graph: dict[str, Any]
    topology: dict[str, Any] | None = None


@dataclass
class CorpusRunResult:
    corpus_id: str
    product_sku: str
    run_id: str
    report_path: str
    summary: dict[str, Any]


@dataclass
class BatchReport:
    batch_id: str
    mode: str
    runs: list[CorpusRunResult]
    aggregate_summary: dict[str, Any] = field(default_factory=dict)


def _sku_for_mode(mode: ProductMode) -> str:
    return PRODUCT_SKUS[mode]


def _build_package(mode: ProductMode, triz_full: dict[str, Any], corpus_id: str) -> dict[str, Any]:
    if mode == "policy_detector":
        return build_policy_package(triz_full, corpus_id)
    if mode == "innovation_radar":
        return build_innovation_package(triz_full, corpus_id)
    return build_narrative_package(triz_full, corpus_id)


def run_corpus_batch(
    corpus_inputs: list[CorpusInput],
    product_mode: ProductMode,
    *,
    batch_mode: BatchMode = "single_corpus",
    tenant: TenantContext,
    output_root: Path | str = "outputs",
    topology_mode: bool = True,
) -> BatchReport:
    """
    Execute TRIZ + product package per corpus; write under outputs/{tenant}/{project}/{run_id}/.
    """
    validate_tenant_context(tenant)
    root = Path(output_root)
    batch_id = str(uuid.uuid4())
    runs: list[CorpusRunResult] = []
    sku = _sku_for_mode(product_mode)

    for inp in corpus_inputs:
        run_id = str(uuid.uuid4())
        out_dir = root / tenant.tenant_id / tenant.project_id / run_id
        assert_tenant_output_path(out_dir, tenant)
        out_dir.mkdir(parents=True, exist_ok=True)

        ag = active_graph_from_payload(inp.active_graph)
        triz = run_triz_analysis_complete(ag, inp.topology, topology_mode=topology_mode)
        pkg = _build_package(product_mode, triz, inp.corpus_id)

        report_path = out_dir / "product_bundle.json"
        report_path.write_text(json.dumps(pkg, indent=2, sort_keys=True), encoding="utf-8")
        triz_path = out_dir / "triz_full.json"
        triz_path.write_text(json.dumps(triz, indent=2, sort_keys=True), encoding="utf-8")

        summary = {
            "corpus_id": inp.corpus_id,
            "global_tension": triz.get("reports", {})
            .get("contradiction_report", {})
            .get("global_tension_index"),
            "contradiction_count": len(triz.get("contradictions", [])),
            "cluster_count": len(triz.get("innovation_clusters", [])),
        }
        runs.append(
            CorpusRunResult(
                corpus_id=inp.corpus_id,
                product_sku=sku,
                run_id=run_id,
                report_path=str(report_path.resolve()),
                summary=summary,
            )
        )

    agg: dict[str, Any] = {"batch_mode": batch_mode, "corpus_count": len(runs)}
    if batch_mode == "time_series_corpus" and len(runs) >= 2:
        agg["tension_trend"] = [r.summary.get("global_tension") for r in runs]
    if batch_mode == "cross_corpus_compare" and len(runs) == 2:
        agg["compare_ready"] = True
        agg["left_corpus"] = runs[0].corpus_id
        agg["right_corpus"] = runs[1].corpus_id

    return BatchReport(batch_id=batch_id, mode=batch_mode, runs=runs, aggregate_summary=agg)
