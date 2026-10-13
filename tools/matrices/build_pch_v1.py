#!/usr/bin/env python3
# HESPERIA — Build and write governed P_CH_v1 (Concept→Hex).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.engine.hex_matrix_builders import HEXES_PER_FAMILY_CANON, NUM_FAMILIES_HEX  # noqa: E402
from core.engine.pch_builder import build_pch_v1, pch_manifest_dict  # noqa: E402
from scipy.sparse import save_npz  # noqa: E402

OUT_DIR = _REPO / "assets" / "matrices" / "pch"
DECAY = 0.12


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mat = build_pch_v1(
        n_concepts=NUM_FAMILIES_HEX,
        n_hex_per_family=HEXES_PER_FAMILY_CANON,
        decay=DECAY,
    )
    save_npz(OUT_DIR / "P_CH_v1.npz", mat)
    manifest = pch_manifest_dict(mat, n_hex_per_family=HEXES_PER_FAMILY_CANON, decay=DECAY)
    (OUT_DIR / "P_CH_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote", OUT_DIR, "nnz=", mat.nnz, "sparsity=", manifest["sparsity"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
