# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topological boundary validator. Validates structural geometry and topology stay within canonical bounds.
Fail-fast on illegal cross-boundary relations. Adjacency matrix is authority for area-level neighborhood.
"""

from __future__ import annotations

from typing import Any

from .geometry_loader import (
    ALLOWED_BOUNDARY_CLASSES,
    ALLOWED_BOUNDARY_TYPES,
    ALLOWED_GEOMETRY_ROLES,
)


def validate_topological_boundaries(
    family_geometry: dict[str, Any],
    area_geometry: dict[str, Any],
    adjacency_matrix: Any,
    family_to_area: Any,
) -> dict[str, Any]:
    """
    Validate area–family partition, family membership, adjacency consistency,
    and that no cross-boundary illegal assignments exist.
    Returns { passed: bool, failed_checks: [...], passed_checks: [...] }.
    """
    failed_set: set[str] = set()
    passed_set: set[str] = set()
    n_areas = 12
    n_families = 288
    valid_area_ids = set(range(n_areas))
    valid_family_indices = set(range(n_families))

    # Resolve adjacency matrix neighbors (support numpy or list of lists)
    def area_neighbors(a: int) -> set[int]:
        out: set[int] = set()
        for j in range(n_areas):
            try:
                if hasattr(adjacency_matrix, "shape"):
                    val = adjacency_matrix[int(a), int(j)]
                else:
                    val = adjacency_matrix[int(a)][int(j)]
                if val == 1:
                    out.add(j)
            except (IndexError, TypeError, KeyError):
                pass
        return out

    # Resolve family_to_area: index -> area_id (support array or list)
    def get_area_for_family(fidx: int) -> int | None:
        try:
            if hasattr(family_to_area, "__getitem__"):
                val = family_to_area[int(fidx)]
                return int(val) if val is not None else None
            return None
        except (IndexError, KeyError, TypeError):
            return None

    families = list(family_geometry.get("families") or [])
    areas = list(area_geometry.get("areas") or [])

    # --- Static geometry: counts ---
    if len(areas) != n_areas:
        failed_set.add("AREA_COUNT_12")
    else:
        passed_set.add("AREA_COUNT_12")

    if len(families) != n_families:
        failed_set.add("FAMILY_COUNT_288")
    else:
        passed_set.add("FAMILY_COUNT_288")

    # --- Family geometry ---
    family_by_index: dict[int, dict[str, Any]] = {}
    for f in families:
        if not isinstance(f, dict):
            continue
        idx = f.get("family_index")
        if idx is None:
            failed_set.add("FAMILY_MISSING_INDEX")
            continue
        idx = int(idx)
        if idx in family_by_index:
            failed_set.add("FAMILY_DUPLICATE_INDEX")
        family_by_index[idx] = f

    if len(family_by_index) == n_families and set(family_by_index.keys()) == valid_family_indices:
        passed_set.add("FAMILY_INDEX_UNIQUE_AND_RANGE")

    fam_ok = True
    for idx, rec in family_by_index.items():
        aid = rec.get("area_id")
        if aid is None:
            failed_set.add("FAMILY_MISSING_AREA_ID")
            fam_ok = False
            break
        if int(aid) not in valid_area_ids:
            failed_set.add("FAMILY_AREA_ID_OUT_OF_RANGE")
            fam_ok = False
            break
        bc = rec.get("boundary_class")
        if bc is not None and bc not in ALLOWED_BOUNDARY_CLASSES:
            failed_set.add("BOUNDARY_CLASSES_VALID")
            fam_ok = False
            break
        neighbors = rec.get("neighbor_families") or []
        if not isinstance(neighbors, (list, tuple)):
            failed_set.add("NEIGHBOR_FAMILIES_LIST")
            fam_ok = False
            break
        for n in neighbors:
            ni = int(n) if n is not None else -1
            if ni not in valid_family_indices:
                failed_set.add("NEIGHBOR_FAMILIES_VALID_INDICES")
                fam_ok = False
                break
        if not fam_ok:
            break
    if fam_ok and "BOUNDARY_CLASSES_VALID" not in failed_set:
        passed_set.add("BOUNDARY_CLASSES_VALID")

    # --- Area geometry ---
    area_by_index: dict[int, dict[str, Any]] = {}
    for a in areas:
        if not isinstance(a, dict):
            continue
        idx = a.get("area_index")
        if idx is None:
            continue
        idx = int(idx)
        if idx in area_by_index:
            failed_set.add("AREA_DUPLICATE_INDEX")
        area_by_index[idx] = a

    area_ok = True
    for idx, rec in area_by_index.items():
        if int(idx) not in valid_area_ids:
            failed_set.add("AREA_INDEX_IN_RANGE")
            area_ok = False
            break
        adj = rec.get("adjacent_areas") or []
        if not isinstance(adj, (list, tuple)):
            failed_set.add("ADJACENT_AREAS_LIST")
            area_ok = False
            break
        for j in adj:
            if int(j) not in valid_area_ids:
                failed_set.add("ADJACENT_AREAS_VALID")
                area_ok = False
                break
        bt = rec.get("boundary_type")
        if bt is not None and bt not in ALLOWED_BOUNDARY_TYPES:
            failed_set.add("BOUNDARY_TYPES_VALID")
            area_ok = False
            break
        gr = rec.get("geometry_role")
        if gr is not None and gr not in ALLOWED_GEOMETRY_ROLES:
            failed_set.add("GEOMETRY_ROLES_VALID")
            area_ok = False
            break
    if area_ok and "ADJACENT_AREAS_VALID" not in failed_set:
        passed_set.add("AREA_ADJACENCY_VALID")

    # --- Partition: every family in exactly one area, union 0..287 ---
    all_members: set[int] = set()
    area_to_families: dict[int, set[int]] = {a: set() for a in range(n_areas)}
    for rec in area_by_index.values():
        aid = int(rec.get("area_index", -1))
        members = rec.get("family_members") or rec.get("family_range")
        if members is None:
            continue
        if isinstance(members, list):
            indices = [int(x) for x in members]
        else:
            indices = []
        for i in indices:
            all_members.add(i)
            if aid in area_to_families:
                area_to_families[aid].add(i)

    if all_members == valid_family_indices and len(all_members) == n_families:
        passed_set.add("FAMILY_AREA_PARTITION_VALID")
    else:
        failed_set.add("FAMILY_AREA_PARTITION_VALID")

    # No family in more than one area
    seen: set[int] = set()
    single_ok = True
    for s in area_to_families.values():
        for i in s:
            if i in seen:
                failed_set.add("FAMILY_SINGLE_AREA")
                single_ok = False
                break
            seen.add(i)
        if not single_ok:
            break
    if single_ok:
        passed_set.add("FAMILY_SINGLE_AREA")

    # --- Adjacency consistency: area_geometry.adjacent_areas == neighbors from matrix ---
    adj_match = True
    for aid in range(n_areas):
        if aid not in area_by_index:
            adj_match = False
            break
        rec = area_by_index[aid]
        spec_adj = set(int(x) for x in (rec.get("adjacent_areas") or []))
        matrix_adj = area_neighbors(aid)
        if spec_adj != matrix_adj:
            adj_match = False
            break
    if adj_match:
        passed_set.add("AREA_ADJACENCY_MATCHES_GEOMETRY")
    else:
        failed_set.add("AREA_ADJACENCY_MATCHES_GEOMETRY")

    # --- Family-to-area consistency: family_geometry[f].area_id == family_to_area[f] ---
    f2a_consistent = True
    for idx in valid_family_indices:
        if idx not in family_by_index:
            f2a_consistent = False
            break
        spec_area = int(family_by_index[idx].get("area_id", -1))
        actual_area = get_area_for_family(idx)
        if actual_area is None or spec_area != actual_area:
            f2a_consistent = False
            break
    if f2a_consistent:
        passed_set.add("FAMILY_TO_AREA_CONSISTENT")
    else:
        failed_set.add("FAMILY_TO_AREA_CONSISTENT")

    # --- Boundary legality: internal no cross-area; edge/corner/bridge only to adjacent areas ---
    boundary_legal = True
    for idx, rec in family_by_index.items():
        my_area = int(rec.get("area_id", -1))
        neighbors = list(rec.get("neighbor_families") or [])
        allowed_areas = {my_area} | area_neighbors(my_area)
        for n in neighbors:
            ni = int(n)
            if ni not in family_by_index:
                continue
            neighbor_area = int(family_by_index[ni].get("area_id", -1))
            if neighbor_area not in allowed_areas:
                boundary_legal = False
                failed_set.add("BOUNDARY_LEGALITY")
                break
        if not boundary_legal:
            break
    if boundary_legal:
        passed_set.add("BOUNDARY_LEGALITY")

    return {
        "passed": len(failed_set) == 0,
        "failed_checks": sorted(failed_set),
        "passed_checks": sorted(passed_set),
    }
