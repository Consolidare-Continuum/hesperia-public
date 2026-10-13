# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 interpretation diagnostics: audit metadata for interpretation.
"""

from __future__ import annotations

from typing import Any


def build_interpretation_diagnostics(
    *,
    dominant_area_id: int | None = None,
    dominance_strength: float | None = None,
    rules_triggered_count: int = 0,
    entropy_after_shadow: float = 0.0,
    tension_after_shadow: float = 0.0,
    propagation_spread: int = 0,
    structural_state_reason: str = "",
    legacy_logic_bridge_used: bool = False,
) -> dict[str, Any]:
    """Build interpretation_diagnostics dict."""
    return {
        "dominant_area_id": dominant_area_id,
        "dominance_strength": dominance_strength,
        "rules_triggered_count": rules_triggered_count,
        "entropy_after_shadow": entropy_after_shadow,
        "tension_after_shadow": tension_after_shadow,
        "propagation_spread": propagation_spread,
        "structural_state_reason": structural_state_reason,
        "legacy_logic_bridge_used": legacy_logic_bridge_used,
    }
