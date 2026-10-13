# HESPERIA — hesperia-dev-test FPF-BUII math battery. Copyright © 2026 igareosh.com.
"""The 'testing ball' for the math inside — reuses tools/fpf_hand_roll_harness.py's existing
ops/dig loop functions directly (no subprocess, no reimplementation) across the full synthetic
corpus instead of the harness's single default sample string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.fpf_hand_roll_harness import _dig_loop, _ops_loop
from tools.hesperia_dev_test.corpus import CorpusEntry, full_corpus

_GAP_REPORT_SCHEMA = "hesperia.fpf_gap_report.v0_1"


@dataclass
class FpfResult:
    entry: CorpusEntry
    ops_ok: bool = False
    dig_ok: bool = False
    gap_count: int | None = None
    slice_count: int | None = None
    error: str | None = None


def run_token(entry: CorpusEntry) -> FpfResult:
    result = FpfResult(entry=entry)
    try:
        ops = _ops_loop(entry.token)
        result.ops_ok = bool(ops.get("ground_truth_keys"))

        dig = _dig_loop(entry.token)
        result.dig_ok = dig.get("gap_schema") == _GAP_REPORT_SCHEMA
        result.gap_count = dig.get("gap_count")
        result.slice_count = dig.get("slice_count")
    except Exception as exc:  # noqa: BLE001
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def run_fpf_battery(corpus: list[CorpusEntry] | None = None) -> list[FpfResult]:
    return [run_token(entry) for entry in (corpus or full_corpus())]


def summarize(results: list[FpfResult]) -> dict[str, Any]:
    by_class: dict[str, dict[str, Any]] = {}
    for r in results:
        bucket = by_class.setdefault(r.entry.cls, {"n": 0, "n_errors": 0, "_gap_counts": []})
        bucket["n"] += 1
        if r.error:
            bucket["n_errors"] += 1
        elif r.gap_count is not None:
            bucket["_gap_counts"].append(r.gap_count)
    for bucket in by_class.values():
        gap_counts = bucket.pop("_gap_counts")
        bucket["mean_gap_count"] = round(sum(gap_counts) / len(gap_counts), 3) if gap_counts else None

    return {
        "n_tokens": len(results),
        "n_ops_ok": sum(1 for r in results if r.ops_ok),
        "n_dig_ok": sum(1 for r in results if r.dig_ok),
        "n_errors": sum(1 for r in results if r.error),
        "by_class": by_class,
    }
