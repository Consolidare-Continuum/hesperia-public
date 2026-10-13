# HESPERIA — RAD. Reverse-trace explainability for bundle metrics (Task 8 v1).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from typing import Any


def explain_metric(
    artifact: dict[str, Any],
    metric_path: str,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Resolve ``metric_path`` on ``artifact`` (simple dot / bracket-lite: ``result.governance``,
    ``sessions[0].result.loopability``) and attach static provenance hints.
    """
    mode = "verbose" if verbose else "compact"
    parts = _parse_path(metric_path)
    cur: Any = artifact
    for p in parts:
        if isinstance(p, int):
            if not isinstance(cur, list) or p >= len(cur):
                return _empty_trace(metric_path, mode, "path_not_found")
            cur = cur[p]
        else:
            if not isinstance(cur, dict):
                return _empty_trace(metric_path, mode, "path_not_found")
            cur = cur.get(p)
            if cur is None:
                return _empty_trace(metric_path, mode, "path_not_found")

    trace: dict[str, Any] = {
        "metric_path": metric_path,
        "value": cur,
        "mode": mode,
    }
    if metric_path.endswith("governance") or ".governance" in metric_path:
        trace.update(
            {
                "source_layers": ["core.math", "core.propagation", "runtime.pipeline.analyze"],
                "upstream_dependencies": ["family_vector", "attribution_coverage"],
                "calculation_path": "analyze() → to_minimal_operational_result → governance",
                "normalization_path": "v06 attribution bundle; scalar in operational band",
            }
        )
    elif "loopability" in metric_path:
        trace.update(
            {
                "source_layers": ["core.math", "propagation"],
                "calculation_path": "analyze() → minimal result.loopability",
            }
        )
    elif "tension_energy" in metric_path or "obstacle_score" in metric_path:
        trace.update(
            {
                "source_layers": ["core.math"],
                "calculation_path": "analyze() → minimal result field",
            }
        )
    elif "ATTRIBUTED_TOKENS" in metric_path or metric_path.endswith("COVERAGE_RATIO"):
        trace.update(
            {
                "source_layers": ["core.layers.layer_1", "hesperia.extensions.dynamics"],
                "calculation_path": "markers_to_concept_activation → compute_L1 (+ optional sealed fallback)",
                "normalization_path": "coverage = attributed / total_tokens",
            }
        )
    elif "hex_activation_map.total_mass" in metric_path or metric_path.endswith("total_mass"):
        trace.update(
            {
                "source_layers": ["core.engine.sealed_multiscale_stack", "core.engine.hex_dynamics"],
                "calculation_path": "concept prior → PCH → microphysics → A1.sum()",
                "signal_loss_stage": "hex_microphysics_line_search" if cur == 0 else None,
            }
        )
    else:
        trace["source_layers"] = []
        trace["calculation_path"] = "unspecified_in_v1"

    if verbose:
        trace["trace_sample"] = _verbose_sample(artifact, metric_path)
    return trace


def _verbose_sample(artifact: dict[str, Any], metric_path: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "sessions" in artifact and artifact["sessions"]:
        s0 = artifact["sessions"][0]
        if isinstance(s0, dict):
            ext = s0.get("extended") or {}
            out["total_tokens"] = ext.get("total_tokens")
            out["matched_tokens"] = ext.get("matched_tokens")
    return out


def _empty_trace(metric_path: str, mode: str, reason: str) -> dict[str, Any]:
    return {
        "metric_path": metric_path,
        "value": None,
        "mode": mode,
        "path_error": reason,
        "source_layers": [],
        "calculation_path": "",
    }


def _parse_path(path: str) -> list[str | int]:
    """Minimal parser: ``a.b`` and ``sessions[0].result.governance``."""
    out: list[str | int] = []
    buf = ""
    i = 0
    while i < len(path):
        c = path[i]
        if c == ".":
            if buf:
                out.append(buf)
                buf = ""
            i += 1
            continue
        if c == "[":
            if buf:
                out.append(buf)
                buf = ""
            j = path.index("]", i)
            out.append(int(path[i + 1 : j].strip()))
            i = j + 1
            continue
        buf += c
        i += 1
    if buf:
        out.append(buf)
    return out
