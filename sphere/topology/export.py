# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topology export: Graphviz DOT and JSON coordinates for icosahedral surface graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from sphere.topology.embedding import get_area_coordinates, UNIT_VERTICES
from sphere.topology.topology_loader import (
    get_canonical_edges,
    get_icosahedral_adjacency,
    META_AREA_INDICES,
)


def project_to_2d(
    x: float, y: float, z: float, eps: float = 1e-9
) -> tuple[float, float]:
    """
    Simple perspective-like projection for 2-D layout; reduces overlap.
    scale = 1 / (2 - z + eps), return (x * scale, y * scale).
    """
    scale = 1.0 / (2.0 - z + eps)
    return (x * scale, y * scale)


def export_icosahedron_graphviz(
    output_path: Optional[Path] = None,
    *,
    adj: Optional[np.ndarray] = None,
    use_coordinates: bool = True,
) -> Path:
    """
    Export icosahedral topology to a Graphviz DOT file.
    Nodes labeled A1..A12; A6 and A12 marked as meta.
    If use_coordinates is True, node positions use 2-D projection of unit-sphere embedding.
    Returns the path where the file was written.
    """
    if adj is None:
        adj = get_icosahedral_adjacency()
    if output_path is None:
        _repo = Path(__file__).resolve().parents[2]
        output_path = _repo / "docs" / "graphs" / "icosahedron_topology.dot"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    edges = get_canonical_edges(adj)
    lines = [
        "// HESPERIA icosahedral surface graph (12 nodes, 30 edges, degree 5)",
        "// Meta nodes: A6, A12",
        "graph icosahedron {",
        "  layout=neato;",
        "  overlap=false;",
        "  splines=true;",
    ]
    coords = get_area_coordinates() if use_coordinates else None
    for i in range(12):
        label = f"A{i + 1}"
        meta = ", shape=doubleoctagon, style=filled, fillcolor=lightgray" if i in META_AREA_INDICES else ""
        if coords is not None:
            x, y, z = coords[i]
            px, py = project_to_2d(x, y, z)
            # Scale for neato (typical scale ~3–5); pos in inches
            scale = 4.0
            pos = f', pos="{scale*px:.4f},{scale*py:.4f}"'
        else:
            pos = ""
        lines.append(f'  node{i} [label="{label}"{meta}{pos}];')
    for i, j in edges:
        lines.append(f"  node{i} -- node{j};")
    lines.append("}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def export_area_coordinates_json(output_path: Optional[Path] = None) -> Path:
    """
    Export area coordinates (A1–A12) to JSON. Format: {"A1": [x,y,z], ...}.
    Returns the path where the file was written.
    """
    if output_path is None:
        _repo = Path(__file__).resolve().parents[2]
        output_path = _repo / "docs" / "graphs" / "icosahedron_coordinates.json"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    coords = get_area_coordinates()
    data = {f"A{i + 1}": [coords[i][0], coords[i][1], coords[i][2]] for i in range(12)}
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return output_path


def export_raw_vs_aligned_coordinates_json(output_path: Optional[Path] = None) -> Path:
    """
    Diagnostic export: raw vertex order (v0..v11) vs aligned area order (A1..A12).
    Format: {"raw": {"v0": [x,y,z], ...}, "aligned": {"A1": [x,y,z], ...}}.
    """
    if output_path is None:
        _repo = Path(__file__).resolve().parents[2]
        output_path = _repo / "docs" / "graphs" / "icosahedron_raw_vs_aligned.json"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aligned = get_area_coordinates()
    data = {
        "raw": {f"v{i}": [UNIT_VERTICES[i][0], UNIT_VERTICES[i][1], UNIT_VERTICES[i][2]] for i in range(12)},
        "aligned": {f"A{i + 1}": [aligned[i][0], aligned[i][1], aligned[i][2]] for i in range(12)},
    }
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return output_path
