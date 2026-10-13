# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
E2E wiring: hex microstructure + Option A closure per text.

v0.5: used by hex_microstructure_tfp artifact + TFP smoke sessions. TFP smoke = testing grounds
per docs/HESPERIA_v0_5_ENGINE_DYNAMICS.md §2 — not canonical release core.

Moved to research/ 2026-07-31 (was hesperia/engine/hex_outputs_e2e.py, briefly hesperia/engine/
hex_outputs/e2e_integration.py before that) — this file's own docstring has always disclaimed
canonical-core status; it belongs with the rest of the non-product research surface, not inside
the engine package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["hex_microstructure_bundle_for_text", "slim_microstructure_for_json"]


def slim_microstructure_for_json(
    micro: dict[str, Any],
    *,
    list_cap: int = 72,
) -> dict[str, Any]:
    """Shrink list payloads for artifacts."""

    def cap_list(x: Any) -> Any:
        if isinstance(x, list):
            if len(x) <= list_cap:
                return x
            return x[:list_cap] + [{"_truncated": True, "_length": len(x)}]
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                if k == "propagation_flow_matrix" and isinstance(v, list):
                    rows = v[: min(24, len(v))]
                    out[k] = [cap_list(row) for row in rows]
                    if len(v) > 24:
                        out[k] = out[k] + [{"_rows_truncated": True, "_nrows": len(v)}]
                else:
                    out[k] = cap_list(v) if isinstance(v, list) else v
            return out
        return x

    out: dict[str, Any] = {}
    for k, v in micro.items():
        if k == "microstructure_propagation" and isinstance(v, dict):
            out[k] = cap_list(dict(v))
        elif isinstance(v, list):
            out[k] = cap_list(v)
        else:
            out[k] = v
    return out


def hex_microstructure_bundle_for_text(
    text: str,
    assets_root: Path,
    *,
    list_cap: int = 72,
    hex_primary_steps: int = 16,
) -> dict[str, Any]:
    """
    Full stack for one text: hits → microstructure analytics + Option A hex dynamics + TFP provenance.
    """
    from hesperia.extensions.dynamics.e2e_bridge import _hits_288
    from core.engine.hex_outputs.hex_output_engine import attach_microstructure_analytics_public

    assets = Path(assets_root)
    hits = _hits_288(text, assets)
    harr = np.asarray(hits, dtype=np.float64)

    micro = attach_microstructure_analytics_public(
        hits, F=288, nh_per_family=12, max_families=40
    )
    micro_slim = slim_microstructure_for_json(micro, list_cap=list_cap)

    from core.engine.hex_dynamics import HexFieldParams, run_option_a_hex_primary
    from core.engine.matrix_loader import load_production_matrices
    from hesperia.system.version import pch_bundle_id

    mats = load_production_matrices()
    C_F = np.asarray(mats["C_F"], dtype=np.float64)
    hp = run_option_a_hex_primary(
        harr,
        C_F,
        n_steps=hex_primary_steps,
        params=HexFieldParams(alpha_H=0.1, beta_H=0.05, gamma_H=0.08, delta_H=0.2, dt=0.04),
    )
    obs = hp["hex_observables_final"]
    hex_primary = {
        "closure": hp["closure"],
        "matrix_bundle_version": mats["bundle_version"],
        "pch_bundle_version": pch_bundle_id(),
        "F_canonical_total": float(np.sum(hp["F_canonical"])),
        "E_H": round(obs.E_H, 6),
        "K_H": round(obs.K_H, 6),
        "G_H": round(obs.G_H, 6),
        "compactness": round(obs.compactness, 6),
        "G_F": round(obs.G_F, 6),
    }

    tfp: dict[str, Any] = {}
    try:
        from sphere.topology.family_embedding import load_family_embedding_tfp

        emb = load_family_embedding_tfp()
        tfp["family_embedding_tfp_loaded"] = True
        tfp["embedding_top_keys"] = list(emb.keys())[:24] if isinstance(emb, dict) else []
    except Exception as e:
        tfp["family_embedding_tfp_loaded"] = False
        tfp["_error"] = str(e)

    try:
        from sphere.topology import load_families_structure_tfp

        fs = load_families_structure_tfp()
        areas = fs.get("areas") or fs.get("by_area")
        if isinstance(areas, dict):
            tfp["families_structure_tfp_n_areas"] = len(areas)
        elif isinstance(areas, list):
            tfp["families_structure_tfp_n_areas"] = len(areas)
    except Exception:
        pass

    return {
        "hits_l1_norm": float(np.sum(harr)),
        "hits_nonzero_families": int(np.count_nonzero(harr)),
        "microstructure_analytics": micro_slim,
        "hex_option_a_summary": hex_primary,
        "tfp_topology": tfp,
    }
