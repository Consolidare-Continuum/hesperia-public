# HESPERIA — RAD. Human readout layer for calibrated metrics (contract v1).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Presentation helpers: band labels + display rounding from ``assets/config/metric_bands_v1.json``.

Does **not** modify attribution or sealed physics — only formats values for UI / audit bundles.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_BANDS_PATH = _REPO / "assets" / "config" / "metric_bands_v1.json"


@lru_cache(maxsize=1)
def _bands_root() -> dict[str, Any]:
    if not _BANDS_PATH.is_file():
        return {"bands": {}}
    return json.loads(_BANDS_PATH.read_text(encoding="utf-8"))


def band_for_value(
    x: float,
    scale: str = "unit_interval",
) -> str:
    """Map ``x`` in [0,1] to a band name (explicit order — first match wins)."""
    root = _bands_root().get("bands") or {}
    spec_block = root.get(scale)
    if not isinstance(spec_block, dict):
        return "unknown"
    xf = float(x)
    order = list(spec_block.keys())
    for name in order:
        spec = spec_block.get(name) or {}
        lo = spec.get("min")
        hi = spec.get("max")
        ok_lo = lo is None or xf >= float(lo)
        ok_hi = hi is None or xf < float(hi)
        if ok_lo and ok_hi:
            return str(name)
    return "unknown"


def format_scalar_readout(
    value_raw: float,
    *,
    scale: str = "unit_interval",
    precision: int = 4,
    interpretation_template: str | None = None,
) -> dict[str, Any]:
    band = band_for_value(float(value_raw), scale=scale)
    dv = round(float(value_raw), int(precision))
    out: dict[str, Any] = {
        "value_raw": float(value_raw),
        "display_value": dv,
        "band": band,
    }
    if interpretation_template:
        out["interpretation"] = interpretation_template.format(band=band, value=dv)
    return out


def expand_governance_style_field(
    name: str,
    value_raw: float,
    *,
    precision: int = 2,
) -> dict[str, Any]:
    """Example target shape from calibration pack Task 3."""
    return {
        name: format_scalar_readout(
            value_raw,
            scale="unit_interval",
            precision=precision,
            interpretation_template="{band} band ({value})",
        )
    }
