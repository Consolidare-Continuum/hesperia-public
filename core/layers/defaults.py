# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# Load L1-L9 predefined defaults. Ref: layer_1_9_predefined_defaults_v1_0.json
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_defaults(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        here = Path(__file__).resolve().parent
        path = here / "layer_1_9_predefined_defaults_v1_0.json"
    if not path or not Path(path).exists():
        return _fallback_defaults()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, Any] = {}
    if "topology" in data:
        out.update(data["topology"])
    if "numerics" in data:
        out["eps"] = data["numerics"].get("eps", 1e-9)
        out["EPS"] = data["numerics"].get("EPS", 1e-12)
        out["EPS_INT"] = data["numerics"].get("EPS_INT", 1e-6)
    for key in ("L2", "L3", "L4", "L5", "L7"):
        if key in data and isinstance(data[key], dict):
            out.update(data[key])
    return out if out else _fallback_defaults()

def _fallback_defaults() -> dict[str, Any]:
    return {
        "F": 288, "A": 12, "FAMILIES_PER_AREA": 24, "FPA": 24,
        "eps": 1e-9, "EPS": 1e-12, "EPS_INT": 1e-6,
        "MAX_ALLOWED_DEPTH": 8,
        "SHADOW_MAX_DEVIATION": 0.25, "SHADOW_MAX_CROSS_AREA_DELTA": 0.10, "SHADOW_ALLOW_AREA_FLIP": False,
        "RETRIEVAL_MODE_ID": "LEX_BM25_V1", "TOP_K": 20, "MAX_SHORTFALL": 2, "MIN_SUPPORT": 0.30, "MAX_DUP_BOOK_CONC": 0.70,
        "MAX_CONTRADICTION": 0.50,
        "MIN_COVERAGE_RATIO": 0.10, "MAX_CROSS_AREA_RATIO": 0.50, "MAX_LYAPUNOV": 2.0, "HIGH_CONF": 0.70, "MED_CONF": 0.40,
        "MIN_PCS": 0.0,  # when > 0 and L1 has profile, L7 gates on PROFILE_CONFORMANCE_SCORE (34_SPEC N1)
    }
