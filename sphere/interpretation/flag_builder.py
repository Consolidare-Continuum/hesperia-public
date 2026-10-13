# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 interpretation flags: derive stable higher-level flags from state + events.
Deterministic and documented.
"""

from __future__ import annotations

from typing import Any


def build_interpretation_flags(
    structural_state: str,
    active_events: list[str],
    logic_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any],
) -> list[str]:
    """
    Build interpretation_flags from structural state and events.
    Flags: stable_focus, structural_concentration, transition_risk, diffusion_noise_controlled, elevated_tension.
    """
    flags: list[str] = []
    if structural_state == "focused_dominant":
        flags.append("structural_concentration")
        if "dominant_area" in active_events:
            flags.append("stable_focus")
    if structural_state == "unstable_transition":
        flags.append("transition_risk")
    if structural_state == "diffuse_spread":
        flags.append("diffusion_noise_controlled")
    if structural_state == "tension_elevated" or "tension_increase" in active_events:
        shadow_diag = shadow_metrics.get("shadow_diagnostics") or {}
        delta = float(shadow_diag.get("tension_after", 0)) - float(shadow_diag.get("tension_before", 0))
        if delta >= 0.10:
            flags.append("elevated_tension")
    if "entropy_drop" in active_events:
        flags.append("structural_concentration")
    return list(dict.fromkeys(flags))  # preserve order, dedupe
