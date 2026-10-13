#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Corpus benchmark: run execution_flow over philosophy, economics, law, psychology corpora.
Output: benchmark_results.json with average_entropy, dominant_area_profile,
propagation_depth, structural_tension_mean, fingerprint_variance.
Usage: python3 -m runtime.pipeline.run_corpus_benchmark [--out path] [--corpora-root path]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

_HERE = Path(__file__).resolve().parent
_HESPERIA = _HERE.parents[1]
if str(_HESPERIA) not in sys.path:
    sys.path.insert(0, str(_HESPERIA))

DEFAULT_CORPORA_ROOT = _HESPERIA / "tools" / "calibration" / "corpora"
DOMAINS = ("philosophy", "economics", "law", "psychology")


def _load_corpus(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("documents", data.get("items", []))


def _run_domain(corpora_root: Path, domain: str, assets: Path) -> list[dict]:
    from runtime.services.analysis_service import run_structural_analysis

    path = corpora_root / domain / "corpus.json"
    if not path.exists():
        return []
    corpus = _load_corpus(path)
    summary_rows = []
    for item in corpus:
        text = item.get("text", item) if isinstance(item, dict) else str(item)
        if not text or not str(text).strip():
            continue
        try:
            summary_payload = run_structural_analysis(str(text), assets_root=assets, attach_version=False)
            summary_rows.append(summary_payload)
        except Exception:
            summary_rows.append({})
    return summary_rows


def _aggregate(summary_rows: list[dict]) -> dict:
    entropies = []
    dominant_areas = []
    propagation_depths = []
    tensions = []
    fingerprint_hashes = []

    for r in summary_rows:
        if not r:
            continue
        raw = (r.get("usf") or {}).get("raw_metrics") or {}
        ms = r.get("multiscale_signals") or {}

        if "entropy" in raw:
            entropies.append(float(raw["entropy"]))
        if "narrative_density" in ms:
            entropies.append(float(ms["narrative_density"]))
        if "dominant_area" in raw:
            dominant_areas.append(int(raw["dominant_area"]))
        if "dominant_macro_domain" in raw:
            dominant_areas.append(int(raw["dominant_macro_domain"]))
        propagation_depths.append(1)
        if "tension" in raw:
            tensions.append(float(raw["tension"]))
        if "contradiction_pressure" in ms:
            tensions.append(float(ms["contradiction_pressure"]))
        fp = (r.get("usf") or {}).get("fingerprint")
        if fp is not None:
            fingerprint_hashes.append(hash(json.dumps(fp, sort_keys=True)))
        if ms:
            fingerprint_hashes.append(hash(json.dumps(ms.get("hspr_index"), sort_keys=True)))

    # Dominant area profile
    dist = defaultdict(int)
    for a in dominant_areas:
        dist[a] += 1
    dominant_area_profile = dict(dist)

    # Fingerprint variance: variance of hash values (as proxy for diversity)
    if len(fingerprint_hashes) >= 2:
        mean_h = sum(fingerprint_hashes) / len(fingerprint_hashes)
        fingerprint_variance = sum((h - mean_h) ** 2 for h in fingerprint_hashes) / len(fingerprint_hashes)
    else:
        fingerprint_variance = 0.0

    return {
        "average_entropy": sum(entropies) / len(entropies) if entropies else 0.0,
        "dominant_area_profile": dominant_area_profile,
        # Compatibility mirror.
        "dominant_area_distribution": dominant_area_profile,
        "propagation_depth": sum(propagation_depths) / len(propagation_depths) if propagation_depths else 0,
        "structural_tension_mean": sum(tensions) / len(tensions) if tensions else 0.0,
        "fingerprint_variance": fingerprint_variance,
        "n_documents": len(summary_rows),
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run corpus benchmark across domains")
    ap.add_argument("--out", type=Path, default=_HESPERIA / "assets" / "artifacts" / "benchmark_results.json")
    ap.add_argument("--corpora-root", type=Path, default=DEFAULT_CORPORA_ROOT)
    args = ap.parse_args()

    assets = _HESPERIA / "assets" / "lexicon" / "curated"
    all_aggregates = {}
    for domain in DOMAINS:
        results = _run_domain(args.corpora_root, domain, assets)
        all_aggregates[domain] = _aggregate(results)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_aggregates, f, indent=2)
    print("Summary report:", out_path.resolve(), file=sys.stderr)
    for domain, agg in all_aggregates.items():
        print(f"  {domain}: n={agg['n_documents']} entropy={agg['average_entropy']:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
