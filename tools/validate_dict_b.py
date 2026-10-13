#!/usr/bin/env python3
# HESPERIA — LEVEL 16 Dict-B validator
# Проверяет: 5–8 concept nodes на семью, уникальные id, observability, area/family, связи.
"""Validate Dict-B concept_nodes.yaml and concept_relations.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DICT_B = REPO / "hesperia" / "ontology" / "dictB"
NODES_PATH = DICT_B / "concept_nodes.yaml"
RELATIONS_PATH = DICT_B / "concept_relations.yaml"

OBSERVABILITY_VALID = frozenset({"высокий", "умеренный", "латентный"})
RELATION_TYPES = frozenset({
    "activates", "opposes", "co_occurs_with", "defends_against",
    "expresses", "observed_in", "part_of", "is_a",
})
EXAMPLE_CONTEXT_STARTS = ("Пациент", "Терапевт", "Когда", "После", "В ходе", "При")
AREAS = [f"A{i}" for i in range(1, 11)]
MIN_NODES_PER_FAMILY = 5
MAX_NODES_PER_FAMILY = 8


def load_yaml(path: Path) -> dict:
    import yaml
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_nodes(nodes: list[dict]) -> tuple[list[str], set[str], dict[tuple[str, str], list[str]]]:
    """Returns (errors, all_ids, family_to_ids)."""
    errors: list[str] = []
    all_ids: set[str] = set()
    family_to_ids: dict[tuple[str, str], list[str]] = {}

    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            errors.append(f"Node {i}: not a dict")
            continue
        nid = n.get("id")
        if not nid:
            errors.append(f"Node {i}: missing id")
            continue
        if not (nid.startswith("B_A") and "_F" in nid and "_" in nid.split("_F")[-1]):
            errors.append(f"Node {nid}: id format must be B_A{{area}}_F{{family}}_{{index}}")
        if nid in all_ids:
            errors.append(f"Duplicate id: {nid}")
        all_ids.add(nid)

        area = n.get("area")
        family = n.get("family")
        if area not in AREAS:
            errors.append(f"Node {nid}: invalid area {area}")
        if not family or not (family.startswith("F") and family[1:].isdigit()):
            errors.append(f"Node {nid}: invalid family {family}")
        if area and family:
            key = (area, family)
            family_to_ids.setdefault(key, []).append(nid)

        obs = n.get("clinical_observability")
        if obs not in OBSERVABILITY_VALID:
            errors.append(f"Node {nid}: invalid clinical_observability '{obs}'")

        label = n.get("label")
        if not label or not isinstance(label, str):
            errors.append(f"Node {nid}: missing or non-string label")

        ctx = n.get("example_context") or ""
        if ctx and not any(ctx.strip().startswith(s) for s in EXAMPLE_CONTEXT_STARTS):
            errors.append(f"Node {nid}: example_context must start with one of {EXAMPLE_CONTEXT_STARTS}")

    for (area, family), ids in family_to_ids.items():
        if len(ids) < MIN_NODES_PER_FAMILY:
            errors.append(f"Family {area}_{family}: has {len(ids)} nodes, minimum {MIN_NODES_PER_FAMILY}")
        if len(ids) > MAX_NODES_PER_FAMILY:
            errors.append(f"Family {area}_{family}: has {len(ids)} nodes, maximum {MAX_NODES_PER_FAMILY}")

    return errors, all_ids, family_to_ids


def validate_relations(relations: list[dict], node_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for i, r in enumerate(relations):
        if not isinstance(r, dict):
            errors.append(f"Relation {i}: not a dict")
            continue
        src = r.get("source")
        tgt = r.get("target")
        rel = r.get("relation") or r.get("type")
        if not src:
            errors.append(f"Relation {i}: missing source")
        if not tgt:
            errors.append(f"Relation {i}: missing target")
        if src and src not in node_ids:
            errors.append(f"Relation {i}: source {src} not in concept nodes")
        if tgt and tgt not in node_ids:
            errors.append(f"Relation {i}: target {tgt} not in concept nodes")
        if rel and rel not in RELATION_TYPES:
            errors.append(f"Relation {i}: unknown relation type '{rel}'")
    return errors


def main() -> int:
    data = load_yaml(NODES_PATH)
    nodes = data.get("nodes") or []
    node_errors, node_ids, family_to_ids = validate_nodes(nodes)

    rel_data = load_yaml(RELATIONS_PATH)
    relations = rel_data.get("relations") or []
    rel_errors = validate_relations(relations, node_ids)

    all_errors = node_errors + rel_errors
    if all_errors:
        for e in all_errors:
            print("ERROR:", e)
        print(f"\nTotal: {len(all_errors)} error(s)")
        return 1

    print("Dict-B validation OK")
    print(f"  Concept nodes: {len(nodes)}")
    print(f"  Families with nodes: {len(family_to_ids)}")
    print(f"  Relations: {len(relations)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
