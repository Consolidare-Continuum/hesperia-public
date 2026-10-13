# HESPERIA — hesperia-dev-test timing probe. Copyright © 2026 igareosh.com.
"""Per-layer timing: wraps sphere.fpf_inspect.probe.probe() individually per CLIMB_ORDER layer,
per synthetic token — composition only, no edits inside sphere/fpf_inspect. Also records the cost
of building the engine_trace itself (the actual analyze + router pipeline), so a report can bucket
cost into {core pipeline, FPF-inspect climb} instead of guessing which layer is heavy.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from sphere.fpf_inspect.constants import CLIMB_ORDER
from sphere.fpf_inspect.probe import probe

from tools.hesperia_dev_test.corpus import CorpusEntry, full_corpus
from tools.hesperia_dev_test.engine_trace import build_dig_input


@dataclass
class TimingResult:
    entry: CorpusEntry
    build_ms: float = 0.0
    layer_ms: dict[str, float] = field(default_factory=dict)
    error: str | None = None


def time_token(entry: CorpusEntry) -> TimingResult:
    result = TimingResult(entry=entry)
    try:
        t0 = time.perf_counter()
        dig_input = build_dig_input(entry.token)
        result.build_ms = (time.perf_counter() - t0) * 1000.0
        for layer_id in CLIMB_ORDER:
            t1 = time.perf_counter()
            probe(layer_id, dig_input)
            result.layer_ms[layer_id] = (time.perf_counter() - t1) * 1000.0
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def run_timing_battery(corpus: list[CorpusEntry] | None = None) -> list[TimingResult]:
    return [time_token(entry) for entry in (corpus or full_corpus())]


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def summarize(results: list[TimingResult]) -> dict[str, Any]:
    per_layer: dict[str, list[float]] = {lid: [] for lid in CLIMB_ORDER}
    build_times: list[float] = []
    for r in results:
        if r.error:
            continue
        build_times.append(r.build_ms)
        for lid, ms in r.layer_ms.items():
            per_layer[lid].append(ms)

    layer_summary: dict[str, dict[str, Any]] = {}
    for lid, samples in per_layer.items():
        if not samples:
            continue
        layer_summary[lid] = {
            "mean_ms": round(statistics.mean(samples), 4),
            "p95_ms": round(_p95(samples), 4),
            "n": len(samples),
        }
    heaviest = max(layer_summary, key=lambda k: layer_summary[k]["mean_ms"]) if layer_summary else None
    sum_probe_mean = round(sum(v["mean_ms"] for v in layer_summary.values()), 4) if layer_summary else 0.0

    return {
        "build_dig_input_mean_ms": round(statistics.mean(build_times), 4) if build_times else None,
        "build_dig_input_p95_ms": round(_p95(build_times), 4) if build_times else None,
        "sum_all_layer_probes_mean_ms": sum_probe_mean,
        "per_layer": layer_summary,
        "heaviest_layer": heaviest,
        "n_tokens": len(results),
        "n_errors": sum(1 for r in results if r.error),
    }
