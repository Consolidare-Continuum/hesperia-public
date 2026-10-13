# HESPERIA — CHI-016 first-class interpret attaches (Layer-9, opt-in TFP-FD, hspr_index honesty).
# Not sealed-core merge. No run_diagnostics. No default-on Field Dynamics.

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from hesperia.modules.tfp.field_dynamics_consumer import (
    TFP_FD_ENV,
    build_tfp_fd_param_envelope,
    tfp_field_dynamics_enabled,
)

_LAYER9_KEY = "layer9_logic"
_TFP_FD_KEY = "tfp_field_dynamics"
_HSPR_KEY = "hspr_index"


def _logic_rules_path(assets_root: Path | None) -> Path | None:
    if assets_root is None:
        return None
    cand = Path(assets_root) / "specs" / "canon" / "logic_rules.yaml"
    return cand if cand.is_file() else None


def facts_from_engine_trace(engine: dict[str, Any]) -> dict[str, Any]:
    """
    Best-effort Layer-9 facts from product interpret engine_trace.
    governance on this path is sealed hspr_index (see engine_analyze_bridge).
    """
    trace = engine.get("trace") or []
    acts = [float(s.get("activation") or 0.0) for s in trace]
    total = sum(acts) or 1.0
    shares = [a / total for a in acts]
    # Shannon entropy over activation shares (normalized)
    entropy = 0.0
    for p in shares:
        if p > 0:
            entropy -= p * math.log(p + 1e-18, 2)
    # normalize roughly to [0,1] vs log2(n)
    n = max(len(shares), 1)
    entropy_n = float(entropy / math.log2(n)) if n > 1 else 0.0
    areas = {
        str(s.get("area_id"))
        for s in trace
        if float(s.get("activation") or 0.0) > 1e-6 and s.get("area_id") is not None
    }
    coverage = float(len(areas) / 12.0)
    return {
        "entropy": round(entropy_n, 6),
        "governance_area": float(engine.get("governance") or 0.0),
        "curvature": float(engine.get("tension_energy") or 0.0),  # proxy; full dynamism not on interpret face
        "coverage": round(coverage, 6),
        "stability_index": float(engine.get("loopability") or 0.0),  # proxy from available face
        "unique_areas": int(len(areas)),
    }


def attach_layer9_logic(
    out: dict[str, Any],
    engine: dict[str, Any],
    *,
    assets_root: Path | None = None,
) -> dict[str, Any]:
    """Single-SoT Layer-9 on interpret — never sphere.diagnostics.run_diagnostics."""
    from sphere.logic import evaluate_rules

    facts = facts_from_engine_trace(engine)
    path = _logic_rules_path(assets_root)
    try:
        logic = evaluate_rules(facts, rule_spec_path=path) if path else evaluate_rules(facts)
    except Exception as exc:  # noqa: BLE001 — face must not fail sealed interpret
        logic = {
            "triggered_rules": [],
            "structural_diagnostics": [],
            "rule_trigger_registry": {"triggered_rule_ids": [], "count": 0},
            "_error": type(exc).__name__,
        }
    out[_LAYER9_KEY] = {
        "schema": "hesperia.layer9_logic.v0",
        "source": "logic_rules.yaml",
        "facts": facts,
        "result": logic,
    }
    return out


def attach_hspr_index_honesty(out: dict[str, Any], engine: dict[str, Any]) -> dict[str, Any]:
    """Live system HSPR KPI (not C4 hspr_field). On interpret face, governance carries sealed hspr_index."""
    out[_HSPR_KEY] = float(engine.get("governance") or 0.0)
    out["hspr_index_note"] = "live_system_hspr_index_via_governance; not_c4_hspr_field"
    return out


def attach_tfp_field_dynamics_opt_in(
    out: dict[str, Any],
    *,
    include_tfp_field_dynamics: bool,
) -> dict[str, Any]:
    """
    Class B opt-in: request flag AND HESPERIA_TFP_FIELD_DYNAMICS env.
    Default path unchanged when either is off.
    """
    if not include_tfp_field_dynamics:
        return out
    if not tfp_field_dynamics_enabled():
        out[_TFP_FD_KEY] = {
            "attached": False,
            "reason": f"env_gate_off:{TFP_FD_ENV}",
            "requested": True,
        }
        return out
    out[_TFP_FD_KEY] = {
        "attached": True,
        "requested": True,
        "env_gate": TFP_FD_ENV,
        "envelope": build_tfp_fd_param_envelope(),
    }
    return out
