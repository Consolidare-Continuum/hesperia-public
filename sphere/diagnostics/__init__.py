# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Structural diagnostics detectors: anomaly, monotony, instability.
#
# CHI-B16-03 / CHI-006 / CHI-016: DEPRECATED as a product Tier-B calibratable pack.
# Zero live callers on /product/interpret (and elsewhere). Canonical live
# diagnostic rules are Layer-9: assets/specs/canon/logic_rules.yaml via
# sphere/logic/rule_engine.py (surfaces: /product/interpret, /product/tfp,
# /product/fingerprint, /product/llm-audit). Do not wire run_diagnostics into
# product_interpret — CHI-016 attaches evaluate_rules only.
from sphere.diagnostics.anomaly_detector import detect_structural_anomalies
from sphere.diagnostics.monotony_detector import (
    detect_structural_monotony,
    compute_dominant_area_share,
)
from sphere.diagnostics.instability_detector import detect_rhetorical_instability
from sphere.diagnostics.diagnostics_runtime import run_diagnostics

__all__ = [
    "detect_structural_anomalies",
    "detect_structural_monotony",
    "compute_dominant_area_share",
    "detect_rhetorical_instability",
    "run_diagnostics",
]
