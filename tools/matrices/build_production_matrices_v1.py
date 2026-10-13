#!/usr/bin/env python3
# HESPERIA — Generate governed production interaction matrices (L_F, C_F, R_F) for bundle v1.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Write ``assets/matrices/production/*.npy`` + ``matrix_manifest.json``. Run from repo root."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.layers.layer_2 import build_canonical_stub_adjacency  # noqa: E402
from hesperia.extensions.dynamics import equations as eq  # noqa: E402
from hesperia.extensions.dynamics.semantic_field_v1 import (  # noqa: E402
    NUM_AREAS,
    NUM_FAMILIES,
    build_family_adjacency_from_sets,
    build_resistance_matrix,
    load_semantic_field_params_v1,
)

OUT_DIR = _REPO / "assets" / "matrices" / "production"
HEX_PER_FAMILY = 12
TOTAL_HEX_CELLS = NUM_FAMILIES * HEX_PER_FAMILY


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    adj = build_canonical_stub_adjacency(NUM_FAMILIES, NUM_AREAS)
    w_f = build_family_adjacency_from_sets(adj)
    l_f = eq.build_family_laplacian(w_f)

    # Inter-area symmetric contradiction (non-trivial off-diagonal), diagonal cleared by builder.
    raw_c = np.zeros((NUM_FAMILIES, NUM_FAMILIES), dtype=np.float64)
    for i in range(NUM_FAMILIES):
        ai = i // (NUM_FAMILIES // NUM_AREAS)
        for j in range(i + 1, NUM_FAMILIES):
            aj = j // (NUM_FAMILIES // NUM_AREAS)
            if ai != aj:
                raw_c[i, j] = raw_c[j, i] = 0.03
    c_f = eq.build_contradiction_matrix(raw_c)

    pr = load_semantic_field_params_v1()
    r_f = build_resistance_matrix(
        np.full(NUM_FAMILIES, float(pr.resistance_uniform), dtype=np.float64)
    )

    np.save(OUT_DIR / "L_F_v1.npy", l_f.astype(np.float64))
    np.save(OUT_DIR / "C_F_v1.npy", c_f.astype(np.float64))
    np.save(OUT_DIR / "R_F_v1.npy", r_f.astype(np.float64))

    manifest = {
        "version": "v1",
        "families": NUM_FAMILIES,
        "hex_per_family": HEX_PER_FAMILY,
        "total_hex_cells": TOTAL_HEX_CELLS,
        "note": "C_F encodes cross-area contradiction structure; L_F from canonical family stub adjacency.",
        "files": {
            "L_F": "L_F_v1.npy",
            "C_F": "C_F_v1.npy",
            "R_F": "R_F_v1.npy",
        },
        "optional_files": {"L_H": None, "C_H": None},
    }
    (OUT_DIR / "matrix_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote", OUT_DIR, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
