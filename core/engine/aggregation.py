"""Engine-owned aggregation from module namespace into final outputs."""

from __future__ import annotations

from typing import Any
from core.engine.conflict_resolver import merge_module_payloads


def _normalize(vector: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(v)) for v in vector.values())
    if total <= 0.0:
        return dict(sorted(vector.items()))
    return {k: max(0.0, float(v)) / total for k, v in sorted(vector.items())}


def aggregate_modules(ctx: dict[str, Any]) -> None:
    module_data = dict(ctx.get("modules") or {})
    merged_metrics: dict[str, Any] = {}
    tfp_conflicts: list[str] = []
    payloads: list[tuple[dict[str, Any], float, int]] = []
    for name, payload in module_data.items():
        if not isinstance(payload, dict):
            continue
        cfg = dict((ctx.get("meta") or {}).get("module_config_resolved", {}).get(name) or {})
        payloads.append((payload, float(cfg.get("weight", 1.0)), int(cfg.get("priority", 0))))
        if isinstance(payload.get("metrics"), dict):
            merged_metrics.update(payload["metrics"])
        tfp_conflicts.extend([str(x) for x in list(payload.get("tfp_conflicts") or [])])
    strategy = str((ctx.get("meta") or {}).get("aggregation_strategy") or "weighted_merge")
    family_scores, area_scores = merge_module_payloads(payloads, strategy)
    ctx["families"] = _normalize(family_scores)
    ctx["areas"] = _normalize(area_scores)
    ctx["metrics"] = merged_metrics
    ctx["signals"]["tfp_conflicts"] = sorted(set(tfp_conflicts))

