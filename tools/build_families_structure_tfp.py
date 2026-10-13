#!/usr/bin/env python3
# HESPERIA — Build families_structure_tfp.yaml from families_master.txt + family_geometry (LEVEL 2 T2.2–T2.4).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Read families_master.txt and family_geometry.yaml; output families_structure_tfp.yaml
with scope (placeholder), included/excluded_phenomena, observability (default умеренный),
family_neighbors (from geometry), family_conflicts, family_complements (empty).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def load_master(path: Path) -> list[dict]:
    """Parse families_master.txt into list of dicts with area_id, family_id, family_name, family_definition."""
    text = path.read_text(encoding="utf-8")
    entries = []
    block: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if block:
                entries.append(block)
                block = {}
            continue
        if "\t" in line:
            key, val = line.split("\t", 1)
            block[key] = val
    if block:
        entries.append(block)
    return entries


def load_geometry(path: Path) -> dict[int, list[int]]:
    """Return family_index -> list of neighbor family_index from family_geometry.yaml."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    out: dict[int, list[int]] = {}
    for fam in data.get("families", []):
        idx = fam.get("family_index")
        if idx is None:
            continue
        neighbors = fam.get("neighbor_families") or []
        out[idx] = [int(n) for n in neighbors if isinstance(n, (int, float))]
    return out


def main() -> None:
    master_path = REPO / "spec" / "families_master.txt"
    geom_path = REPO / "spec" / "family_geometry.yaml"
    out_path = REPO / "spec" / "families_structure_tfp.yaml"
    if len(sys.argv) > 1:
        master_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        geom_path = Path(sys.argv[2])
    if len(sys.argv) > 3:
        out_path = Path(sys.argv[3])

    if not master_path.exists():
        print(f"Master not found: {master_path}", file=sys.stderr)
        sys.exit(1)
    if not geom_path.exists():
        print(f"Geometry not found: {geom_path}", file=sys.stderr)
        sys.exit(1)

    entries = load_master(master_path)
    geo = load_geometry(geom_path)

    # family_id (family_001) -> index 0
    def id_to_index(fid: str) -> int:
        return int(fid.replace("family_", "")) - 1

    def index_to_id(i: int) -> str:
        return f"family_{i + 1:03d}"

    families: list[dict] = []
    for e in entries:
        fid = e.get("family_id", "")
        idx = id_to_index(fid)
        neighbor_indices = geo.get(idx, [])
        # Only operational families 0..239
        neighbor_ids = [index_to_id(n) for n in neighbor_indices if 0 <= n < 240]
        families.append({
            "family_id": fid,
            "area_id": e.get("area_id", ""),
            "family_name": e.get("family_name", ""),
            "scope": e.get("family_definition", ""),  # placeholder = definition
            "included_phenomena": [],
            "excluded_phenomena": [],
            "observability": "умеренный",
            "family_neighbors": neighbor_ids,
            "family_conflicts": [],
            "family_complements": [],
        })
    out = {
        "version": 1,
        "domain": "TFP_KERNBERG",
        "description": "LEVEL 2 family structure: scope, observability, adjacency. 240 operational families.",
        "families": families,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(out, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)
    print(f"Wrote {len(families)} families to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
