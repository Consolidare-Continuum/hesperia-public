#!/usr/bin/env python3
# HESPERIA — RAD. family_weights → family_weights_sparse (graph sparsification).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build family_weights_sparse.json from full matrix + concept clusters.")
    ap.add_argument("--family-weights", type=Path, required=True, help="family_weights.json or family_contradiction_matrix.json")
    ap.add_argument("--concept-clusters", type=Path, required=True, help="concept_clusters.json (clusters[].concepts or .families)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-effective-weight", action="store_true", help="Omit log(1+overlap) scaling on effective_weight")
    ap.add_argument("--include-matrix", action="store_true", help="Write full matrix_sparse (large)")
    args = ap.parse_args()

    from hesperia.extensions.triz.family_weights_sparsify import run_sparsify_from_paths

    try:
        body = run_sparsify_from_paths(
            args.family_weights,
            args.concept_clusters,
            use_effective_weight=not args.no_effective_weight,
        )
    except ValueError as e:
        print(f"VALIDATION_FAIL: {e}", file=sys.stderr)
        return 1
    if not args.include_matrix:
        body = {k: v for k, v in body.items() if k != "matrix_sparse"}
        body["matrix_sparse_omitted"] = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out} edges={body.get('edge_count')} avg_deg={body.get('avg_degree')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
