# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-4 Topology Graph loader.
Loads area adjacency matrix and family→area mapping; builds topology graph for runtime.
Icosahedral surface graph: 12 nodes, 30 edges, degree 5 per node. Meta nodes A6 (5), A12 (11).
Deterministic, validated. No propagation logic — data definition + loader only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Default data directory: repo_root/assets/topology
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _REPO_ROOT / "assets" / "topology"

ADJACENCY_FILENAME = "area_adjacency_matrix.json"
FAMILY_AREA_FILENAME = "family_to_area_map.json"

# Icosahedral surface graph invariants
from core.topology.invariant_catalog import AREAS as NUM_AREAS

ICOSAHEDRAL_DEGREE = 5
ICOSAHEDRAL_EDGES = 30
# Meta reference nodes (A6, A12): semantic control anchors; propagation weight reduced
META_AREA_INDICES = frozenset({5, 11})

# Canonical icosahedral adjacency = geometric icosahedron (unit-sphere embedding).
# 12×12, 30 edges, degree 5. A1=0 .. A12=11. Aligned to build_coordinate_edge_graph(UNIT_VERTICES).
ICOSAHEDRAL_ADJACENCY_LIST: tuple[tuple[int, ...], ...] = (
    (1, 5, 7, 10, 11),  # A1
    (0, 5, 7, 8, 9),    # A2
    (3, 4, 6, 10, 11),  # A3
    (2, 4, 6, 8, 9),    # A4
    (2, 3, 5, 9, 11),   # A5
    (0, 1, 4, 9, 11),   # A6 meta
    (2, 3, 7, 8, 10),   # A7
    (0, 1, 6, 8, 10),   # A8
    (1, 3, 6, 7, 9),    # A9
    (1, 3, 4, 5, 8),    # A10
    (0, 2, 6, 7, 11),   # A11
    (0, 2, 4, 5, 10),   # A12 meta
)


def get_icosahedral_adjacency() -> np.ndarray:
    """Return the canonical 12×12 icosahedral adjacency matrix (in-memory, no file)."""
    adj = np.zeros((NUM_AREAS, NUM_AREAS), dtype=np.int64)
    for i, neighbors in enumerate(ICOSAHEDRAL_ADJACENCY_LIST):
        for j in neighbors:
            adj[i, j] = 1
    return adj


def _data_dir(data_root: Optional[Path] = None) -> Path:
    return Path(data_root) if data_root is not None else _DEFAULT_DATA_DIR


def _neighbors_from_adjacency(adjacency_matrix: np.ndarray) -> dict[int, list[int]]:
    """Build neighbor list per node from 12×12 adjacency matrix."""
    n = adjacency_matrix.shape[0]
    return {i: [j for j in range(n) if adjacency_matrix[i, j] == 1] for i in range(n)}


def _is_connected(adjacency_matrix: np.ndarray) -> bool:
    """True if graph is a single connected component (BFS from node 0)."""
    neighbors = _neighbors_from_adjacency(adjacency_matrix)
    seen = set()
    stack = [0]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for j in neighbors.get(node, []):
            if j not in seen:
                stack.append(j)
    return len(seen) == adjacency_matrix.shape[0]


def validate_icosahedral(adjacency_matrix: np.ndarray) -> None:
    """
    Enforce icosahedral invariants: strict symmetry, zero diagonal, binary entries,
    degree 5 per node, 30 edges, single connected component.
    Raises ValueError on violation.
    """
    adj = np.asarray(adjacency_matrix)
    n = adj.shape[0] if hasattr(adj, "shape") else len(adj)
    if n != NUM_AREAS:
        raise ValueError(f"icosahedral adjacency must have n={NUM_AREAS}, got {n}")

    def get_val(i: int, j: int) -> int:
        if hasattr(adj, "shape"):
            return int(adj[i, j])
        return int(adj[i][j])

    edge_count = 0
    for i in range(n):
        if get_val(i, i) != 0:
            raise ValueError(f"icosahedral diagonal must be 0, got adj[{i}][{i}]={get_val(i, i)}")
        row_sum = 0
        for j in range(n):
            v = get_val(i, j)
            if v not in (0, 1):
                raise ValueError(f"icosahedral entries must be binary (0 or 1), got adj[{i}][{j}]={v}")
            if v != get_val(j, i):
                raise ValueError(
                    f"icosahedral matrix must be symmetric, got adj[{i}][{j}]={v} != adj[{j}][{i}]={get_val(j, i)}"
                )
            row_sum += v
        if row_sum != ICOSAHEDRAL_DEGREE:
            raise ValueError(
                f"icosahedral degree rule: every node must have degree {ICOSAHEDRAL_DEGREE}, "
                f"node {i} has degree {row_sum}"
            )
        edge_count += row_sum

    if edge_count // 2 != ICOSAHEDRAL_EDGES:
        raise ValueError(
            f"icosahedral edge count must be {ICOSAHEDRAL_EDGES}, got {edge_count // 2}"
        )
    if not _is_connected(adj):
        raise ValueError("icosahedral graph must be connected (single component)")


def canonical_edge_list(adj: np.ndarray | list[list[Any]]) -> list[tuple[int, int]]:
    """
    Deterministic edge list for hashing and reproducibility.
    Returns sorted list of (i, j) with i < j for each edge.
    """
    a = np.asarray(adj)
    n = a.shape[0]
    edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if a[i, j]:
                edges.append((i, j))
    edges.sort()
    return edges


def get_canonical_edges(adj: np.ndarray | None = None, data_root: Optional[Path] = None) -> list[tuple[int, int]]:
    """
    Return canonical edge list for the loaded or given adjacency matrix.
    If adj is None, loads from data_root (default: file).
    """
    if adj is None:
        adj = load_area_adjacency(data_root)
    return canonical_edge_list(adj)


def topology_fingerprint(adj: np.ndarray | list[list[Any]]) -> str:
    """
    SHA256 fingerprint of adjacency matrix for provenance and integrity checks.
    Deterministic: same matrix → same hex digest.
    """
    a = np.asarray(adj, dtype=np.int64)
    data = json.dumps(a.tolist(), separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(data.encode()).hexdigest()


def load_area_adjacency(data_root: Optional[Path] = None) -> np.ndarray:
    """
    Load the 12×12 binary area adjacency matrix (icosahedral surface graph).
    Returns: adjacency_matrix (np.ndarray, shape (12, 12), dtype int64).
    Raises on invalid shape, non-symmetric, non-zero diagonal, or icosahedral violation
    (degree != 5, edges != 30, graph not connected).
    """
    path = _data_dir(data_root) / ADJACENCY_FILENAME
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("matrix")
    if raw is None:
        raise ValueError(f"{path}: missing 'matrix' key")
    adjacency_matrix = np.array(raw, dtype=np.int64)
    # Basic validation
    if adjacency_matrix.shape != (NUM_AREAS, NUM_AREAS):
        raise ValueError(
            f"area adjacency matrix must have shape ({NUM_AREAS}, {NUM_AREAS}), got {adjacency_matrix.shape}"
        )
    if not np.array_equal(adjacency_matrix, adjacency_matrix.T):
        raise ValueError("area adjacency matrix must be symmetric")
    if np.any(np.diag(adjacency_matrix) != 0):
        raise ValueError("area adjacency matrix diagonal must be 0")
    if np.any((adjacency_matrix != 0) & (adjacency_matrix != 1)):
        raise ValueError("area adjacency matrix must be binary (0 or 1)")
    validate_icosahedral(adjacency_matrix)
    return adjacency_matrix


def load_family_area_mapping(data_root: Optional[Path] = None) -> np.ndarray:
    """
    Load the canonical family→area mapping (288 families → area index 0–11).
    Returns: family_to_area (np.ndarray, shape (288,), dtype int64).
    family_to_area[i] = area index for family index i (0-based).
    Raises on wrong size or invalid area ids.
    """
    path = _data_dir(data_root) / FAMILY_AREA_FILENAME
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    mapping = data.get("mapping")
    if mapping is None:
        raise ValueError(f"{path}: missing 'mapping' key")
    # Build array in canonical order: family_001 .. family_288 → indices 0..287
    family_to_area = np.zeros(288, dtype=np.int64)
    for i in range(1, 289):
        key = f"family_{i:03d}"
        if key not in mapping:
            raise ValueError(f"{path}: missing key '{key}' in mapping")
        a = int(mapping[key])
        if not (0 <= a < 12):
            raise ValueError(
                f"{path}: invalid area id {a} for '{key}' (must be 0–11)"
            )
        family_to_area[i - 1] = a
    if len(mapping) != 288:
        raise ValueError(
            f"family_to_area mapping must have exactly 288 entries, got {len(mapping)}"
        )
    return family_to_area


def build_topology_graph(data_root: Optional[Path] = None) -> dict:
    """
    Build the topology graph from the area adjacency matrix (icosahedral).
    Returns dict with:
      - "nodes": 12
      - "areas": 12 (alias)
      - "neighbors": { area_index: [list of adjacent area indices] }
      - "edges": 30
      - "degree": 5
      - "fingerprint": SHA256 hex digest of adjacency matrix
      - "coordinates": dict[area_index, (x,y,z)] unit-sphere embedding
    Uses load_area_adjacency; raises on validation failure.
    """
    from sphere.topology.embedding import coordinate_fingerprint, get_area_coordinates

    adjacency_matrix = load_area_adjacency(data_root)
    neighbors = _neighbors_from_adjacency(adjacency_matrix)
    total_edges = int(adjacency_matrix.sum()) // 2
    fp = topology_fingerprint(adjacency_matrix)
    coordinates = get_area_coordinates()  # aligned to topology
    coord_fp = coordinate_fingerprint(coordinates)
    return {
        "nodes": NUM_AREAS,
        "areas": NUM_AREAS,
        "neighbors": neighbors,
        "edges": total_edges,
        "degree": ICOSAHEDRAL_DEGREE,
        "fingerprint": fp,
        "coordinate_fingerprint": coord_fp,
        "coordinates": coordinates,
    }


def load_all(
    data_root: Optional[Path] = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Load adjacency matrix, family→area mapping, and topology graph.
    Returns (adjacency_matrix, family_to_area, topology_graph).
    All validation is performed; raises on any violation.
    """
    adjacency_matrix = load_area_adjacency(data_root)
    family_to_area = load_family_area_mapping(data_root)
    topology_graph = build_topology_graph(data_root)
    # Cross-checks (icosahedral + mapping)
    assert adjacency_matrix.shape == (NUM_AREAS, NUM_AREAS), adjacency_matrix.shape
    assert len(family_to_area) == 288, len(family_to_area)
    assert np.array_equal(adjacency_matrix, adjacency_matrix.T), "adjacency symmetric"
    assert np.all((family_to_area >= 0) & (family_to_area < NUM_AREAS)), "no invalid area ids"
    assert topology_graph["edges"] == ICOSAHEDRAL_EDGES, f"edges must be {ICOSAHEDRAL_EDGES}"
    return adjacency_matrix, family_to_area, topology_graph
