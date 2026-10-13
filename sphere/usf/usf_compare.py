# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF comparison: deterministic structural delta between two USF artifacts.
Reports deltas only; no interpretation prose.
"""

from __future__ import annotations

from typing import Any


def compare_scalar(metric_name: str, a: Any, b: Any) -> dict[str, Any]:
    """Compare two scalar values. Returns {a, b, delta, changed} for numerics."""
    try:
        va, vb = float(a), float(b)
        delta = vb - va
        return {"a": va, "b": vb, "delta": delta, "changed": va != vb}
    except (TypeError, ValueError):
        return {"a": a, "b": b, "delta": None, "changed": a != b}


def compare_vectors(vec_a: Any, vec_b: Any) -> dict[str, Any]:
    """
    Compare two numeric vectors. Equal length required.
    Returns L1 distance and list of indices where values differ.
    """
    if not isinstance(vec_a, (list, tuple)) or not isinstance(vec_b, (list, tuple)):
        return {"l1": None, "changed_indices": [], "equal_length": False}
    if len(vec_a) != len(vec_b):
        return {"l1": None, "changed_indices": [], "equal_length": False}
    l1 = sum(abs(float(x) - float(y)) for x, y in zip(vec_a, vec_b, strict=True))
    changed = [i for i in range(len(vec_a)) if vec_a[i] != vec_b[i]]
    return {"l1": l1, "changed_indices": changed, "equal_length": True}


def compare_usf(usf_a: dict[str, Any], usf_b: dict[str, Any]) -> dict[str, Any]:
    """
    Produce deterministic structural delta report between two USFs.
    Inspects raw metrics, dynamism, propagation (vectors), and logic outputs.
    """
    out: dict[str, Any] = {
        "usf_a_version": usf_a.get("usf_version", ""),
        "usf_b_version": usf_b.get("usf_version", ""),
        "same_schema_version": usf_a.get("usf_version") == usf_b.get("usf_version"),
        "metric_deltas": {},
        "dominant_changes": {},
        "vector_deltas": {},
        "logic_changes": {},
    }

    # Scalars from raw_metrics
    raw_a = usf_a.get("raw_metrics") or {}
    raw_b = usf_b.get("raw_metrics") or {}
    for key in ("entropy", "tension", "loopability", "coverage"):
        if key in raw_a and key in raw_b:
            out["metric_deltas"][key] = compare_scalar(key, raw_a[key], raw_b[key])

    # Dominant
    for key in ("dominant_area", "dominant_family"):
        if key in raw_a and key in raw_b:
            a_val, b_val = raw_a[key], raw_b[key]
            out["dominant_changes"][key] = {"a": a_val, "b": b_val, "changed": a_val != b_val}

    # Dynamism scalars
    dyn_a = usf_a.get("dynamism_metrics") or {}
    dyn_b = usf_b.get("dynamism_metrics") or {}
    for key in ("curvature", "stability_index"):
        if key in dyn_a and key in dyn_b:
            out["metric_deltas"][key] = compare_scalar(key, dyn_a[key], dyn_b[key])
    if "jump_rate" in dyn_a and "jump_rate" in dyn_b:
        ja = dyn_a["jump_rate"] if isinstance(dyn_a["jump_rate"], (int, float)) else dyn_a.get("jump_rate", {}).get("jump_rate", 0.0)
        jb = dyn_b["jump_rate"] if isinstance(dyn_b["jump_rate"], (int, float)) else dyn_b.get("jump_rate", {}).get("jump_rate", 0.0)
        out["metric_deltas"]["jump_rate"] = compare_scalar("jump_rate", ja, jb)

    # Vector deltas
    av_a = (raw_a.get("area_vector") or []) if isinstance(raw_a.get("area_vector"), (list, tuple)) else []
    av_b = (raw_b.get("area_vector") or []) if isinstance(raw_b.get("area_vector"), (list, tuple)) else []
    av_cmp = compare_vectors(av_a, av_b)
    out["vector_deltas"]["area_vector_l1"] = av_cmp.get("l1")
    out["vector_deltas"]["area_vector_changed_indices"] = av_cmp.get("changed_indices", [])

    fc_a = (raw_a.get("family_counts") or []) if isinstance(raw_a.get("family_counts"), (list, tuple)) else []
    fc_b = (raw_b.get("family_counts") or []) if isinstance(raw_b.get("family_counts"), (list, tuple)) else []
    fc_cmp = compare_vectors(fc_a, fc_b)
    out["vector_deltas"]["family_counts_l1"] = fc_cmp.get("l1")

    # Logic
    logic_a = usf_a.get("logic_outputs") or {}
    logic_b = usf_b.get("logic_outputs") or {}
    triggered_a = {r.get("rule_id") for r in (logic_a.get("triggered_rules") or []) if isinstance(r, dict) and r.get("rule_id")}
    triggered_b = {r.get("rule_id") for r in (logic_b.get("triggered_rules") or []) if isinstance(r, dict) and r.get("rule_id")}
    flags_a = set(logic_a.get("logic_flags") or [])
    flags_b = set(logic_b.get("logic_flags") or [])

    out["logic_changes"]["triggered_rules_added"] = sorted(triggered_b - triggered_a)
    out["logic_changes"]["triggered_rules_removed"] = sorted(triggered_a - triggered_b)
    out["logic_changes"]["logic_flags_added"] = sorted(flags_b - flags_a)
    out["logic_changes"]["logic_flags_removed"] = sorted(flags_a - flags_b)

    return out
