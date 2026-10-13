#!/usr/bin/env python3
# HESPERIA — Reference Architecture Definition (RAD)
# Generate deterministic demo artifacts from benchmark corpora.

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]  # repo root (examples/extensions/triz_demo/triz/this_file)
sys.path.insert(0, str(_ROOT))
_BENCH = _ROOT / "hesperia" / "extensions" / "triz" / "benchmarks"
_OUT = Path(__file__).resolve().parent / "outputs"
_ASSETS = Path(__file__).resolve().parent / "assets"


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def main() -> None:
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
    from hesperia.product.investor_demo import build_investor_snapshot
    from hesperia.product.package_builder import (
        build_innovation_package,
        build_narrative_package,
        build_policy_package,
    )
    _OUT.mkdir(parents=True, exist_ok=True)
    _ASSETS.mkdir(parents=True, exist_ok=True)

    # Demo 1: policy coherent vs polarized
    pol_c = _BENCH / "corpus_policy_coherent"
    pol_p = _BENCH / "corpus_policy_polarized"
    spec_c = json.loads((pol_c / "graph.json").read_text(encoding="utf-8"))
    spec_p = json.loads((pol_p / "graph.json").read_text(encoding="utf-8"))
    triz_c = run_triz_analysis_complete(
        active_graph_from_payload(spec_c["active_graph"]), spec_c.get("topology")
    )
    triz_p = run_triz_analysis_complete(
        active_graph_from_payload(spec_p["active_graph"]), spec_p.get("topology")
    )
    pkg_c = build_policy_package(triz_c, "policy_coherent_v1")
    pkg_p = build_policy_package(triz_p, "policy_polarized_v1")
    _write(_OUT / "demo1_policy_coherent.json", json.dumps(pkg_c, indent=2, sort_keys=True))
    _write(_OUT / "demo1_policy_polarized.json", json.dumps(pkg_p, indent=2, sort_keys=True))
    exec_c = (
        f"# Executive view — Policy (coherent vs polarized)\n\n"
        f"**Coherent** tension: {pkg_c['report']['global_tension_score']:.2f}\n\n"
        f"**Polarized** tension: {pkg_p['report']['global_tension_score']:.2f}\n\n"
        f"{pkg_p['report']['summary_text']}\n"
    )
    _write(_OUT / "demo1_executive.md", exec_c)
    side = (
        f"| Corpus | Global tension | SKU |\n|:---|---:|---|\n"
        f"| Coherent | {pkg_c['report']['global_tension_score']:.2f} | {pkg_c['sku']} |\n"
        f"| Polarized | {pkg_p['report']['global_tension_score']:.2f} | {pkg_p['sku']} |\n"
    )
    _write(_OUT / "demo1_side_by_side.md", side)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["corpus", "global_tension_score", "sku"])
    w.writerow(["coherent", pkg_c["report"]["global_tension_score"], pkg_c["sku"]])
    w.writerow(["polarized", pkg_p["report"]["global_tension_score"], pkg_p["sku"]])
    _write(_OUT / "demo1_policy_flat.csv", buf.getvalue())

    # Demo 2: innovation
    inn = _BENCH / "corpus_innovation_sparse"
    si = json.loads((inn / "graph.json").read_text(encoding="utf-8"))
    triz_i = run_triz_analysis_complete(active_graph_from_payload(si["active_graph"]), si.get("topology"))
    pkg_i = build_innovation_package(triz_i, "innovation_sparse_v1")
    _write(_OUT / "demo2_innovation_radar.json", json.dumps(pkg_i, indent=2, sort_keys=True))
    w2 = io.StringIO()
    cw = csv.writer(w2)
    cw.writerow(["cluster_id", "innovation_score", "concepts"])
    for c in pkg_i["report"]["strongest_clusters"]:
        cw.writerow([c.get("cluster_id"), c.get("innovation_score"), "|".join(c.get("concepts") or [])])
    _write(_OUT / "demo2_clusters.csv", w2.getvalue())
    _write(
        _OUT / "demo2_summary.md",
        f"# Innovation Radar demo\n\n{pkg_i['report']['summary_text']}\n",
    )

    # Demo 3: narrative spillover
    nar = _BENCH / "corpus_narrative_spillover"
    sn = json.loads((nar / "graph.json").read_text(encoding="utf-8"))
    triz_n = run_triz_analysis_complete(active_graph_from_payload(sn["active_graph"]), sn.get("topology"))
    pkg_n = build_narrative_package(triz_n, "narrative_spillover_v1")
    _write(_OUT / "demo3_narrative_monitor.json", json.dumps(pkg_n, indent=2, sort_keys=True))
    w3 = io.StringIO()
    cw3 = csv.writer(w3)
    cw3.writerow(["step", "area", "activation"])
    for r in pkg_n["report"]["top_routes"]:
        cw3.writerow([r.get("step"), r.get("area"), r.get("activation")])
    _write(_OUT / "demo3_routes.csv", w3.getvalue())
    inv = build_investor_snapshot("narrative_spillover_v1", triz_n, product="Narrative Monitor")
    _write(_OUT / "demo3_investor_snapshot.json", json.dumps(inv, indent=2, sort_keys=True))
    blk = ", ".join(str(x) for x in (pkg_n["report"].get("blocked_routes") or [])[:8])
    _write(
        _OUT / "demo3_executive.md",
        f"# Narrative monitor\n\n{pkg_n['report']['summary_text']}\n\nBlockage map: {blk}\n",
    )

    print("Demo outputs written to", _OUT)


if __name__ == "__main__":
    main()
