# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 structural rule event types and thresholds.
Deterministic; no math implementation — thresholds are constants.
"""

from __future__ import annotations

# Rule thresholds (deterministic structural conditions)
DOMINANT_AREA_SHARE_THRESHOLD = 0.35
ENTROPY_DROP_THRESHOLD = 0.15
TENSION_INCREASE_THRESHOLD = 0.10
PROPAGATION_SPREAD_AREAS_THRESHOLD = 2

# Event type identifiers
EVENT_DOMINANT_AREA = "dominant_area"
EVENT_ENTROPY_DROP = "entropy_drop"
EVENT_TENSION_INCREASE = "tension_increase"
EVENT_PROPAGATION_SPREAD = "propagation_spread"
EVENT_DOMINANCE_TRANSITION = "dominance_transition"
