# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# Load R1-R4 ESM defaults (Part D). Ref: r1_r4_esm_defaults_v1_0.json, docs/SPEC__Reading_Scale_Levels_R1_R4_Structural_Audit_v1_0.md
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULTS_PATH = Path(__file__).resolve().parent / "r1_r4_esm_defaults_v1_0.json"


def load_r1_r4_esm_defaults(path: Path | None = None) -> dict[str, Any]:
    """Load R1-R4 ESM defaults (top_n, delta_expected, epsilon, sigma bounds, R3 typing, etc.)."""
    p = path if path is not None else _DEFAULTS_PATH
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_top_n(defaults: dict[str, Any] | None = None) -> int:
    """Top-N for leakage/coverage; constant across R-levels (spec §2.2). Default 3."""
    if defaults is None:
        defaults = load_r1_r4_esm_defaults()
    return int(defaults.get("top_n", 3))
