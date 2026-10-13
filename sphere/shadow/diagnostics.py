# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Shadow diagnostics: report what was suppressed, boost applied, entropy and tension change.
"""

from __future__ import annotations

from typing import Any


def build_shadow_diagnostics(
    *,
    tail_suppression_count: int = 0,
    structural_threshold: float = 0.0,
    mass_retained_after_suppression: float = 0.0,
    dominance_boost_factor: float = 0.0,
    entropy_before: float = 0.0,
    entropy_after: float = 0.0,
    tension_before: float = 0.0,
    tension_after: float = 0.0,
    normalized: bool = True,
) -> dict[str, Any]:
    """Build deterministic shadow diagnostics dict."""
    return {
        "tail_suppression_count": tail_suppression_count,
        "structural_threshold": structural_threshold,
        "mass_retained_after_suppression": mass_retained_after_suppression,
        "dominance_boost_factor": dominance_boost_factor,
        "entropy_before": entropy_before,
        "entropy_after": entropy_after,
        "entropy_change": entropy_after - entropy_before,
        "tension_before": tension_before,
        "tension_after": tension_after,
        "tension_change": tension_after - tension_before,
        "normalized": normalized,
    }
