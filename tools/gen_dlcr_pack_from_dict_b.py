#!/usr/bin/env python3
"""Generate DLCR dict_a/dict_b JSONL from hesperia ontology concept_nodes (TFP Kernberg).

Writes:
  assets/data/engine_dynamics_v060/dict_b/dict_b_tfp.jsonl
  assets/data/engine_dynamics_v060/dict_a/dict_a_tfp.jsonl
  assets/data/engine_dynamics_v060/anchors/concept_hex_anchors_tfp.json (merged with seed anchors)

Keeps deterministic order (sorted concept id). Caps at --max-nodes (default 220).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hesperia.ontology.dictB.loader import load_concept_nodes

AREA_OK = re.compile(r"^A([1-9]|10)$")
FAM_OK = re.compile(r"^F([0-9]+)$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-nodes", type=int, default=220)
    args = ap.parse_args()

    nodes = load_concept_nodes()
    eligible: list[dict] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        cid = n.get("id")
        area = n.get("area")
        fam = n.get("family")
        label = n.get("label")
        definition = n.get("definition") or label
        if not cid or not label or not AREA_OK.match(str(area)) or not FAM_OK.match(str(fam)):
            continue
        eligible.append(
            {
                "concept_id": str(cid),
                "preferred_label": str(label).strip(),
                "definition": str(definition).strip()[:2000],
                "area": str(area),
                "family": str(fam),
            }
        )
    eligible.sort(key=lambda x: x["concept_id"])
    picked = eligible[: max(1, min(args.max_nodes, len(eligible)))]

    out_b = REPO / "assets" / "data" / "engine_dynamics_v060" / "dict_b" / "dict_b_tfp.jsonl"
    out_a = REPO / "assets" / "data" / "engine_dynamics_v060" / "dict_a" / "dict_a_tfp.jsonl"
    out_b.parent.mkdir(parents=True, exist_ok=True)
    out_a.parent.mkdir(parents=True, exist_ok=True)

    anchors: dict[str, str] = {}
    lines_b: list[str] = []
    lines_a: list[str] = []
    for i, row in enumerate(picked):
        hx = f"HX-{i + 1:04d}"
        cid = row["concept_id"]
        anchors[cid] = hx
        fam_id = row["family"]
        area_id = row["area"]
        brec = {
            "concept_id": cid,
            "preferred_label": row["preferred_label"],
            "definition": row["definition"],
            "family_ids": [fam_id],
            "area_ids": [area_id],
            "specificity_rank": min(99, len(row["preferred_label"]) % 20 + 1),
            "status": "active",
            "version": "v0.6.0-tfp",
            "hex_anchor": hx,
        }
        lines_b.append(json.dumps(brec, ensure_ascii=False))
        # Lexical: normalized lowercase Russian label; phrase match
        norm = row["preferred_label"].casefold().strip()
        if not norm:
            continue
        arec = {
            "entry_id": f"TFP-A-{i + 1:05d}",
            "surface_form": row["preferred_label"],
            "normalized_form": norm,
            "match_type": "phrase" if " " in norm else "exact",
            "candidate_concept_ids": [cid],
            "priority": 5,
            "version": "v0.6.0-tfp",
            "language": "ru",
        }
        lines_a.append(json.dumps(arec, ensure_ascii=False))

    out_b.write_text("\n".join(lines_b) + "\n", encoding="utf-8")
    out_a.write_text("\n".join(lines_a) + "\n", encoding="utf-8")

    anchors_path = REPO / "assets" / "data" / "engine_dynamics_v060" / "anchors" / "concept_hex_anchors_tfp.json"
    anchors_path.parent.mkdir(parents=True, exist_ok=True)
    seed_anchors = REPO / "assets" / "data" / "engine_dynamics_v060" / "anchors" / "concept_hex_anchors.json"
    merged = {}
    if seed_anchors.exists():
        merged.update(json.loads(seed_anchors.read_text(encoding="utf-8")))
    merged.update(anchors)
    anchors_path.write_text(json.dumps(dict(sorted(merged.items())), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    hx_vals = sorted(set(merged.values()))
    hx_index = {hx: idx for idx, hx in enumerate(hx_vals)}
    hx_map_path = REPO / "assets" / "data" / "engine_dynamics_v060" / "anchors" / "hex_index_map.json"
    hx_map_path.write_text(json.dumps(hx_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Russian gold lines: text = label, expect same normalized span
    corp = REPO / "assets" / "data" / "engine_dynamics_v060" / "corpora" / "gold_tfp_ru.jsonl"
    corp.parent.mkdir(parents=True, exist_ok=True)
    gold_lines = []
    seen_norm: set[str] = set()
    for row in picked:
        lab = row["preferred_label"].strip()
        norm = lab.casefold().strip()
        if len(norm) < 12 or norm in seen_norm:
            continue
        seen_norm.add(norm)
        gold_lines.append(
            json.dumps(
                {
                    "corpus_id": "gold_tfp_ru",
                    "text": lab,
                    "spans": [{"span": norm, "winner": row["concept_id"]}],
                },
                ensure_ascii=False,
            )
        )
        if len(gold_lines) >= 40:
            break
    corp.write_text("\n".join(gold_lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(lines_b)} dict_b, {len(lines_a)} dict_a, {len(merged)} anchors, {len(gold_lines)} gold_tfp_ru lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
