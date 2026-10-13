# HESPERIA — hesperia-dev-test orchestration. Copyright © 2026 igareosh.com.
"""Runs the full battery (api_battery -> timing_probe -> alphabet_map -> fpf_battery) and writes
one JSON report."""

from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.hesperia_dev_test import alphabet_map, api_battery, bench0, fpf_battery, timing_probe
from tools.hesperia_dev_test.corpus import bench0_latin, full_corpus


def _serialize_api_results(results: list[api_battery.TokenResult]) -> list[dict[str, Any]]:
    return [
        {
            "id": r.entry.id,
            "token": r.entry.token,
            "class": r.entry.cls,
            "analyze_status": r.analyze_status,
            "interpret_status": r.interpret_status,
            "analyze_ms": round(r.analyze_ms, 4),
            "interpret_ms": round(r.interpret_ms, 4),
            "deterministic": r.deterministic,
            "error": r.error,
        }
        for r in results
    ]


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def _api_summary(results: list[api_battery.TokenResult]) -> dict[str, Any]:
    ok = [r for r in results if not r.error and r.analyze_status == 200 and r.interpret_status == 200]
    lat = [r.analyze_ms for r in ok] + [r.interpret_ms for r in ok]
    non_deterministic = [r.entry.token for r in results if r.deterministic is False]

    by_class: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_class.setdefault(r.entry.cls, {"n": 0, "n_ok": 0, "n_error": 0})
        bucket["n"] += 1
        if r.error:
            bucket["n_error"] += 1
        elif r.analyze_status == 200 and r.interpret_status == 200:
            bucket["n_ok"] += 1

    return {
        "n_tokens": len(results),
        "n_ok": len(ok),
        "n_errors": sum(1 for r in results if r.error),
        "non_deterministic_tokens": non_deterministic,
        "latency_ms": {
            "mean": round(statistics.mean(lat), 4) if lat else None,
            "p95": round(_p95(lat), 4) if lat else None,
            "max": round(max(lat), 4) if lat else None,
        },
        "by_class": by_class,
    }


def run(
    *,
    live_base_url: str | None = None,
    out_path: Path | None = None,
    full: bool = False,
) -> dict[str, Any]:
    """Default (full=False): bench0_latin lane only — fast, CI/agent path (Colombo Bench-0
    design). full=True: full_corpus soak (adds digit/bool/index/diacritic lanes, observational
    only, not gold-checked).
    """
    t_start = time.perf_counter()
    corpus = full_corpus() if full else bench0_latin()

    client = api_battery.live_client(live_base_url) if live_base_url else api_battery.in_process_client()
    try:
        api_results = api_battery.run_battery(client, corpus=corpus)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()

    timing_results = timing_probe.run_timing_battery(corpus=corpus)
    alpha_map = alphabet_map.build_alphabet_map()
    fpf_results = fpf_battery.run_fpf_battery(corpus=corpus)
    bench0_results = bench0.run_bench0()  # always bench0_latin, own in-process client

    total_ms = (time.perf_counter() - t_start) * 1000.0

    report: dict[str, Any] = {
        "schema": "hesperia.dev_test_report.v0_1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live_base_url else "in_process",
        "live_base_url": live_base_url,
        "corpus": "full" if full else "bench0_latin",
        "total_wall_ms": round(total_ms, 2),
        "bench0": bench0.summarize(bench0_results),
        "api_battery": {
            "summary": _api_summary(api_results),
            "results": _serialize_api_results(api_results),
        },
        "timing_probe": timing_probe.summarize(timing_results),
        "alphabet_map": {
            "summary": alphabet_map.summarize(alpha_map),
            "letters": alpha_map,
        },
        "fpf_battery": fpf_battery.summarize(fpf_results),
    }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    return report


def print_summary(report: dict[str, Any]) -> None:
    bench0_summary = report["bench0"]
    api = report["api_battery"]["summary"]
    timing = report["timing_probe"]
    alpha = report["alphabet_map"]["summary"]
    fpf = report["fpf_battery"]

    print(f"hesperia-dev-test [{report['mode']}, corpus={report['corpus']}] — total {report['total_wall_ms']} ms")
    print(
        f"  bench0 (gold): {bench0_summary['n_ok']}/{bench0_summary['n_tokens']} ok, "
        f"{bench0_summary['n_failing']} failing"
    )
    if bench0_summary["n_failing"]:
        for token, violations in bench0_summary["violations"].items():
            print(f"    {token}: {violations}")
    print(
        f"  api_battery: {api['n_ok']}/{api['n_tokens']} ok, {api['n_errors']} errors, "
        f"non_deterministic={api['non_deterministic_tokens']}, "
        f"latency ms mean/p95/max = {api['latency_ms']['mean']}/{api['latency_ms']['p95']}/{api['latency_ms']['max']}"
    )
    print(
        f"  timing_probe: heaviest_layer={timing['heaviest_layer']}, "
        f"build_dig_input(core pipeline) mean_ms={timing['build_dig_input_mean_ms']}, "
        f"sum_all_layer_probes mean_ms={timing['sum_all_layer_probes_mean_ms']}"
    )
    for layer_id, s in timing["per_layer"].items():
        print(f"    {layer_id}: mean={s['mean_ms']}ms p95={s['p95_ms']}ms n={s['n']}")
    print(
        f"  alphabet_map: {alpha['n_letters']} letters, {alpha['n_errors']} errors, "
        f"area_distribution={alpha['area_distribution']}"
    )
    print(
        f"  fpf_battery: ops_ok={fpf['n_ops_ok']}/{fpf['n_tokens']}, "
        f"dig_ok={fpf['n_dig_ok']}/{fpf['n_tokens']}, errors={fpf['n_errors']}"
    )
    for cls, bucket in fpf["by_class"].items():
        print(f"    {cls}: n={bucket['n']} errors={bucket['n_errors']} mean_gap_count={bucket['mean_gap_count']}")
