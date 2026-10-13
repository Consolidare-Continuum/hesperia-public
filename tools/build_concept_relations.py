#!/usr/bin/env python3
# HESPERIA — Генерация плотного semantic concept graph для Dict-B (≈2000–4000 связей).
# Правила: intra-family (co_occurs_with), intra-area (activates, defends_against),
# cross-area (activates), opposing (opposes). Без self-loop, уникальные связи.
"""Build concept_relations.yaml with 2000–4000 relations for full Dict-B graph."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DICT_B = REPO / "hesperia" / "ontology" / "dictB"
SPEC = REPO / "spec"

RELATION_TYPES = frozenset({
    "activates", "opposes", "co_occurs_with", "defends_against",
    "expresses", "observed_in",
})

# Теоретические мосты TFP: область → область (activates)
CROSS_AREA_CHAINS = [
    ("A1", "A2"),   # drives → object relations
    ("A2", "A3"),   # object relations → defenses
    ("A3", "A4"),   # defenses → aggression
    ("A4", "A6"),   # aggression → narcissism
    ("A6", "A7"),   # narcissism → love pathology
    ("A8", "A9"),   # diagnosis → technique
    ("A9", "A10"),  # technique → treatment process
]

# Противоположности (area, family) ↔ (area, family) для opposes
OPPOSING_PAIRS = [
    (("A2", "F6"), ("A3", "F1")),   # integration ↔ splitting
    (("A2", "F6"), ("A3", "F2")),   # integration ↔ idealization/devaluation
    (("A7", "F1"), ("A4", "F1")),   # empathy/love ↔ rage
    (("A7", "F11"), ("A4", "F2")),  # gratitude ↔ hatred
    (("A10", "F6"), ("A4", "F2")),  # reparation ↔ destruction
    (("A3", "F14"), ("A3", "F1")),  # repression ↔ splitting
    (("A2", "F5"), ("A2", "F6")),   # identity diffusion ↔ consolidation
    (("A2", "F2"), ("A2", "F6")),   # split object ↔ integrated object
    (("A4", "F24"), ("A4", "F1")),  # regulation ↔ rage
    (("A1", "F2"), ("A1", "F3")),   # libido ↔ aggression
]


def load_yaml(path: Path) -> dict:
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def family_id_to_area_flocal(family_id: str) -> tuple[str, str]:
    """family_001 -> (A1, F1); family_025 -> (A2, F1)."""
    num = int(str(family_id).replace("family_", ""))
    area_idx = (num - 1) // 24 + 1
    local = (num - 1) % 24 + 1
    return f"A{area_idx}", f"F{local}"


def build_concept_ids_by_af(nodes: list[dict]) -> dict[tuple[str, str], list[str]]:
    """(area, family) -> sorted list of concept ids."""
    by_af: dict[tuple[str, str], list[str]] = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        cid = n.get("id")
        area = n.get("area")
        fam = n.get("family")
        if cid and area and fam:
            key = (str(area), str(fam))
            by_af.setdefault(key, []).append(cid)
    for key in by_af:
        by_af[key].sort()
    return by_af


def add_intra_family(relations: set[tuple[str, str, str]], by_af: dict) -> None:
    """6 nodes per family → 15 pairs, type co_occurs_with."""
    for (area, fam), ids in by_af.items():
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if a != b:
                    relations.add((a, b, "co_occurs_with"))


def add_intra_area(
    relations: set[tuple[str, str, str]],
    by_af: dict,
    families_data: list[dict],
) -> None:
    """Same-area family neighbors: activates and defends_against."""
    fid_to_af = {}
    for fam in families_data:
        fid = fam.get("family_id")
        area = fam.get("area_id")
        if not fid or not area:
            continue
        _, flocal = family_id_to_area_flocal(fid)
        fid_to_af[fid] = (str(area), flocal)
    for fam in families_data:
        fid = fam.get("family_id")
        neighbors = fam.get("family_neighbors") or []
        if fid not in fid_to_af:
            continue
        area_a, fam_a = fid_to_af[fid]
        ids_a = by_af.get((area_a, fam_a))
        if not ids_a:
            continue
        for nb_id in neighbors:
            if nb_id not in fid_to_af:
                continue
            area_b, fam_b = fid_to_af[nb_id]
            if area_a != area_b:
                continue
            ids_b = by_af.get((area_b, fam_b))
            if not ids_b:
                continue
            # One activates, one defends_against (deterministic)
            c1, c2 = ids_a[0], ids_b[0]
            if c1 != c2:
                relations.add((c1, c2, "activates"))
            c3, c4 = ids_a[1] if len(ids_a) > 1 else ids_a[0], ids_b[1] if len(ids_b) > 1 else ids_b[0]
            if c3 != c4:
                relations.add((c3, c4, "defends_against"))


def add_cross_area(
    relations: set[tuple[str, str, str]],
    by_af: dict,
    max_per_chain: int = 25,
) -> None:
    """Cross-area chains: activates (e.g. A1→A2, A2→A3)."""
    areas = [f"A{i}" for i in range(1, 11)]
    for area_a, area_b in CROSS_AREA_CHAINS:
        ids_a = []
        ids_b = []
        for (ar, fam), cids in by_af.items():
            if ar == area_a:
                ids_a.extend(cids)
            if ar == area_b:
                ids_b.extend(cids)
        if not ids_a or not ids_b:
            continue
        n = 0
        for i in range(min(max_per_chain, len(ids_a))):
            for j in range(min(max_per_chain, len(ids_b))):
                if n >= max_per_chain:
                    break
                sa, tb = ids_a[i], ids_b[j]
                if sa != tb:
                    relations.add((sa, tb, "activates"))
                    n += 1
            if n >= max_per_chain:
                break


def add_opposing(
    relations: set[tuple[str, str, str]],
    by_af: dict,
) -> None:
    """Opposing pairs: opposes."""
    for (area_a, fam_a), (area_b, fam_b) in OPPOSING_PAIRS:
        ids_a = by_af.get((area_a, fam_a))
        ids_b = by_af.get((area_b, fam_b))
        if not ids_a or not ids_b:
            continue
        for sa in ids_a[:2]:
            for tb in ids_b[:2]:
                if sa != tb:
                    relations.add((sa, tb, "opposes"))


def main() -> int:
    import yaml
    import argparse
    parser = argparse.ArgumentParser(description="Build concept_relations.yaml (2000–4000 relations)")
    parser.add_argument("--max-relations", type=int, default=0, help="Cap total relations (e.g. 4000)")
    args = parser.parse_args()
    nodes_path = DICT_B / "concept_nodes.yaml"
    families_path = SPEC / "families_structure_tfp.yaml"
    if not nodes_path.exists():
        print("Missing", nodes_path, file=sys.stderr)
        return 1
    if not families_path.exists():
        print("Missing", families_path, file=sys.stderr)
        return 1
    nodes_data = load_yaml(nodes_path)
    families_data = load_yaml(families_path).get("families") or []
    nodes = nodes_data.get("nodes") or []
    by_af = build_concept_ids_by_af(nodes)
    relations: set[tuple[str, str, str]] = set()
    add_intra_family(relations, by_af)
    add_intra_area(relations, by_af, families_data)
    add_cross_area(relations, by_af)
    add_opposing(relations, by_af)
    # Deduplicate and no self-loops
    unique = set()
    out_list = []
    for s, t, rel in relations:
        if s == t:
            continue
        key = (s, t, rel)
        if key in unique:
            continue
        unique.add(key)
        out_list.append({"source": s, "relation": rel, "target": t})
    out_list.sort(key=lambda r: (r["source"], r["relation"], r["target"]))
    if args.max_relations > 0 and len(out_list) > args.max_relations:
        out_list = out_list[: args.max_relations]
        print(f"Capped to {len(out_list)} relations (--max-relations={args.max_relations})")
    out = {
        "version": 1,
        "domain": "TFP_KERNBERG",
        "language": "ru",
        "description": (
            "Плотный semantic concept graph Dict-B. "
            "Intra-family (co_occurs_with), intra-area (activates, defends_against), "
            "cross-area (activates), opposing (opposes)."
        ),
        "relation_count": len(out_list),
        "relations": out_list,
    }
    out_path = DICT_B / "concept_relations.yaml"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# LEVEL 16 — Связи между концептами Dict-B (плотный граф 2000–4000).\n")
        f.write("# Типы: activates, opposes, co_occurs_with, defends_against, expresses, observed_in\n\n")
        yaml.dump(out, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=100)
    print(f"Wrote {len(out_list)} relations to {out_path}")
    if not (2000 <= len(out_list) <= 5000):
        print(f"Note: target 2000–4000; got {len(out_list)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
