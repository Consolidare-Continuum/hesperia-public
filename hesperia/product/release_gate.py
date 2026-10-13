# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Pre-demo / pre-external run readiness checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hesperia.extensions.triz.guards import TrizStructuralViolation, guard_no_meta_lexical_activation
from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
from research.evaluation.baselines.compare import run_triz_vs_baselines
from research.evaluation.triz_evaluator import (
    evaluate_innovation_radar,
    evaluate_narrative_monitor,
    evaluate_policy_detector,
)
from hesperia.product.dashboard_contracts import build_dashboard_bundle, validate_dashboard_bundle


@dataclass
class ProductReadinessGate:
    passed: bool
    failures: list[str] = field(default_factory=list)
    benchmark_summary: dict[str, Any] = field(default_factory=dict)
    schema_summary: dict[str, Any] = field(default_factory=dict)


def _scores_in_unit_interval(obj: Any, path: str = "", errs: list[str] | None = None) -> list[str]:
    if errs is None:
        errs = []
    if isinstance(obj, float):
        if obj < -1e-9 or obj > 1.0 + 1e-9:
            errs.append(f"score out of [0,1] at {path}: {obj}")
    elif isinstance(obj, dict):
        for k, v in sorted(obj.items()):
            _scores_in_unit_interval(v, f"{path}.{k}", errs)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scores_in_unit_interval(v, f"{path}[{i}]", errs)
    return errs


def _deterministic_rerun(triz_full: dict[str, Any], ag_payload: dict, topo: Any) -> bool:
    from hesperia.extensions.triz.pipeline import active_graph_from_payload as agf

    ag = agf(ag_payload)
    second = run_triz_analysis_complete(ag, topo, topology_mode=True)
    a = json.dumps(triz_full, sort_keys=True)
    b = json.dumps(second, sort_keys=True)
    return a == b


def run_release_gate(
    *,
    benchmark_root: Path | None = None,
    fit_threshold: float = 0.12,
) -> ProductReadinessGate:
    failures: list[str] = []
    bench_sum: dict[str, Any] = {}
    schema_sum: dict[str, Any] = {"dashboard_ok": True}

    root = benchmark_root or Path(__file__).resolve().parents[2] / "hesperia" / "extensions" / "triz" / "benchmarks"
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        failures.append("benchmark manifest missing")
        return ProductReadinessGate(False, failures, bench_sum, schema_sum)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for b in manifest.get("benchmarks", []):
        bid = b.get("id", "?")
        sub = root / b.get("corpus_dir", "")
        if not sub.is_dir():
            failures.append(f"benchmark dir missing: {bid}")
            continue
        try:
            cmp = run_triz_vs_baselines(sub)
            spec = json.loads((sub / "graph.json").read_text(encoding="utf-8"))
            ag = active_graph_from_payload(spec["active_graph"])
            triz = run_triz_analysis_complete(ag, spec.get("topology"), topology_mode=True)
        except TrizStructuralViolation as e:
            failures.append(f"guard violation {bid}: {e}")
            continue
        except Exception as e:
            failures.append(f"benchmark run failed {bid}: {e}")
            continue

        ev = b.get("evaluator", "policy")
        prof = b.get("expected_profile", {})
        if ev == "policy":
            r = evaluate_policy_detector(triz.get("reports", {}).get("contradiction_report", {}), prof)
        elif ev == "innovation":
            r = evaluate_innovation_radar(triz.get("reports", {}).get("innovation_report", {}), prof)
        else:
            r = evaluate_narrative_monitor(triz, prof)
        fit = float(r.get("profile_fit_score", 0))
        bench_sum[bid] = {"fit": fit, "detail": r}
        if fit < fit_threshold:
            failures.append(f"benchmark fit below threshold: {bid} ({fit} < {fit_threshold})")

        se = _scores_in_unit_interval(triz.get("narratives", []))
        for cl in triz.get("innovation_clusters", []):
            v = float(cl.get("innovation_score", 0))
            if v < -1e-9 or v > 1.0 + 1e-9:
                se.append(f"innovation_score OOB: {v}")
        for c in triz.get("contradictions", []):
            v = float(c.get("score", 0))
            if v < -1e-9 or v > 1.0 + 1e-9:
                se.append(f"contradiction score OOB: {v}")
        if se:
            failures.extend(se[:8])

        if not _deterministic_rerun(triz, spec["active_graph"], spec.get("topology")):
            failures.append(f"non-deterministic triz output: {bid}")

        dash = build_dashboard_bundle(triz)
        verr = validate_dashboard_bundle(dash)
        if verr:
            schema_sum["dashboard_ok"] = False
            failures.extend([f"dashboard {bid}: {x}" for x in verr])

    try:
        guard_no_meta_lexical_activation({"x": 5})
        failures.append("meta-area guard did not fire on synthetic input")
    except TrizStructuralViolation:
        pass

    try:
        run_triz_vs_baselines(root / "corpus_policy_polarized")
    except Exception as e:
        failures.append(f"baseline comparison failed: {e}")

    return ProductReadinessGate(len(failures) == 0, failures, bench_sum, schema_sum)
