# HESPERIA — TFP Class B Field Dynamics consumer (CHI-015 A1).
# Gated by HESPERIA_TFP_FIELD_DYNAMICS (default off). Not sealed core. Not interpret-by-default.
# Agentic address map (items 93–126): docs/recipes/chiron_tweaks/CHIRON-126-ADDRESS-MAP-2026-08-21.md

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hesperia.extensions.dynamics.state import Phase1Theta, Phase3Theta, Phase4Theta
from hesperia.extensions.dynamics.semantic_field_v1 import SemanticFieldParamsV1
from hesperia.engine.calibration.hspr_field import HSPRWeights

TFP_FD_CONSUMER_ID = "tfp.field_dynamics_consumer.v0"
TFP_FD_ENV = "HESPERIA_TFP_FIELD_DYNAMICS"
TFP_FD_ENVELOPE_SCHEMA = "tfp_fd_param_envelope_v1"

# Ξ boost blend constants (bound from xi_proxy.apply path — surface honesty, not retune)
XI_BLEND_G = 0.35
XI_BLEND_PER = 0.65

C1_KEYS = (
    "hex_cap",
    "lambda_h",
    "theta_c",
    "theta_d",
    "theta_p",
    "mu_h",
    "delta_h",
    "rho_h",
    "hex_hit_blend",
)
C2_KEYS = ("gravity_epsilon", "tau_front", "ephemeral_cap")
C3_KEYS = ("xi_scale", "xi_kme_weight", "xi_blend_g", "xi_blend_per")
C4_KEYS = ("w_sigma", "w_Q", "w_E", "w_K", "w_R", "w_D", "source_alignment_kappa")
C5_KEYS = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "mu",
    "dt",
    "epsilon",
    "tau",
    "resistance_uniform",
    "production_clip",
    "signed_source_experimental",
)


def tfp_field_dynamics_enabled() -> bool:
    """Master Class B gate — default off."""
    return os.environ.get(TFP_FD_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _xi_defaults() -> dict[str, float]:
    from hesperia.extensions.dynamics import xi_proxy

    scale = float(xi_proxy._xi_scale_from_env())  # noqa: SLF001 — bind live default
    kme_w = float(xi_proxy._xi_kme_weight_from_env())  # noqa: SLF001 — same SoT as apply path (0.55)
    return {
        "xi_scale": scale,
        "xi_kme_weight": kme_w,
        "xi_blend_g": XI_BLEND_G,
        "xi_blend_per": XI_BLEND_PER,
    }


def build_tfp_fd_param_envelope() -> dict[str, Any]:
    """
    Class B param envelope for gated TFP-FD (CHI-015).
    C1–C3–C5 → S-ENV values from live defaults; C4 → S-OFF weights only.
    """
    th3 = Phase3Theta()
    th4 = Phase4Theta()
    sf = SemanticFieldParamsV1()
    hw = HSPRWeights()
    c1 = {k: getattr(th3, k) for k in C1_KEYS}
    c2 = {k: getattr(th4, k) for k in C2_KEYS}
    c3 = _xi_defaults()
    c4 = {**asdict(hw), "source_alignment_kappa": 1.0, "surface": "S-OFF", "runtime_score": False}
    c5 = {k: getattr(sf, k) for k in C5_KEYS}
    return {
        "schema": TFP_FD_ENVELOPE_SCHEMA,
        "consumer_id": TFP_FD_CONSUMER_ID,
        "packs": {
            "c1_phase3": c1,
            "c2_phase4": c2,
            "c3_xi": c3,
            "c4_hspr_offline": c4,
            "c5_semantic_field": c5,
        },
        "key_counts": {
            "c1": len(C1_KEYS),
            "c2": len(C2_KEYS),
            "c3": len(C3_KEYS),
            "c4": len(C4_KEYS),
            "c5": len(C5_KEYS),
            "total_34": len(C1_KEYS) + len(C2_KEYS) + len(C3_KEYS) + len(C4_KEYS) + len(C5_KEYS),
        },
    }


def run_tfp_hspr_offline_calib_job(out_dir: Path) -> dict[str, Any]:
    """
    CHI-015 C4 B1-shaped offline job: write HSPR weight SoT + empty grid stub.
    Does **not** emit runtime HSPR into product interpret.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = build_tfp_fd_param_envelope()
    c4 = dict(env["packs"]["c4_hspr_offline"])
    report = {
        "schema": "tfp_hspr_offline_calib_v1",
        "consumer_id": TFP_FD_CONSUMER_ID,
        "mode": "B1_offline_meta_cal",
        "runtime_score": False,
        "weights": {k: c4[k] for k in C4_KEYS if k in c4},
        "note": "Grid-search campaign optional; SoT weights accommodated under TFP calib only.",
    }
    path = out_dir / "tfp_hspr_offline_calib.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["path"] = str(path)
    return report


def run_tfp_field_dynamics_artifact(
    text: str,
    assets_root: Path,
    out_dir: Path,
    *,
    theta: Phase1Theta | None = None,
    include_dynamics_run: bool = False,
) -> dict[str, Any]:
    """
    Thin export over ``run_field_dynamics_e2e_artifact`` + param envelope.

    Gate-off: skipped (no envelope packs).
    Gate-on: always attach ``tfp_fd_envelope`` (34-param honesty). Optional full
    dynamics run when ``include_dynamics_run=True`` (composes research FD env).
    """
    if not tfp_field_dynamics_enabled():
        return {
            "consumer_id": TFP_FD_CONSUMER_ID,
            "tfp_field_dynamics": False,
            "_skipped": True,
            "reason": f"{TFP_FD_ENV} not set",
        }

    envelope = build_tfp_fd_param_envelope()
    out: dict[str, Any] = {
        "consumer_id": TFP_FD_CONSUMER_ID,
        "tfp_field_dynamics": True,
        "tfp_fd_envelope": envelope,
    }

    if not include_dynamics_run:
        return out

    from hesperia.extensions.dynamics.e2e_bridge import run_field_dynamics_e2e_artifact

    prev = os.environ.get("HESPERIA_FIELD_DYNAMICS")
    os.environ["HESPERIA_FIELD_DYNAMICS"] = "1"
    try:
        raw = run_field_dynamics_e2e_artifact(text, assets_root, out_dir, theta=theta)
    finally:
        if prev is None:
            os.environ.pop("HESPERIA_FIELD_DYNAMICS", None)
        else:
            os.environ["HESPERIA_FIELD_DYNAMICS"] = prev

    if not isinstance(raw, dict):
        raw = {"payload": raw}
    out.update(raw)
    out["consumer_id"] = TFP_FD_CONSUMER_ID
    out["tfp_field_dynamics"] = True
    out["tfp_fd_envelope"] = envelope
    return out
