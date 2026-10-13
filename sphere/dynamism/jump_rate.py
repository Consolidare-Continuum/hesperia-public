# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-6 jump rate — orchestration only; math lives in core.math.
"""

from __future__ import annotations

from core.math.curvature_metrics import compute_jump_rate

__all__ = ["compute_jump_rate"]
