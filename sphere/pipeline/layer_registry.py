# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA central layer registry.
Pipeline runner imports layers from here only; no hardcoded layer imports elsewhere.
Deterministic ordering: L1 → L2 → … → L9. RAD: registry lives in sphere (sphere → core only).
"""

from __future__ import annotations

import core.layers.layer_1 as layer_1
import core.layers.layer_2 as layer_2
import core.layers.layer_3 as layer_3
import core.layers.layer_4 as layer_4
import core.layers.layer_5 as layer_5
import core.layers.layer_6 as layer_6
import core.layers.layer_7 as layer_7
import core.layers.layer_8 as layer_8
import core.layers.layer_9 as layer_9

LAYERS = [
    (1, layer_1),
    (2, layer_2),
    (3, layer_3),
    (4, layer_4),
    (5, layer_5),
    (6, layer_6),
    (7, layer_7),
    (8, layer_8),
    (9, layer_9),
]
