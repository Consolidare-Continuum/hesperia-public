# HESPERIA — Session graph visualization and export
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Export Clinical ActiveGraph to GEXF/GraphML; activation heatmap; area trajectory plot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def export_graph_gexf(graph: dict[str, Any], path: str | Path) -> None:
    """
    Export hierarchical graph (nodes, edges) to GEXF XML.
    graph["nodes"]: list of {id, node_type, weight, area_id, ...}
    graph["edges"]: list of {source, target, edge_type, weight}
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("gexf", version="1.2")
    root.set("xmlns", "http://www.gexf.net/1.2draft")
    meta = ET.SubElement(root, "meta", lastmodifieddate="2026-01-01")
    ET.SubElement(meta, "creator").text = "HESPERIA"
    graph_el = ET.SubElement(root, "graph", mode="static", defaultedgetype="directed")
    nodes_el = ET.SubElement(graph_el, "nodes")
    for n in graph.get("nodes") or []:
        node_el = ET.SubElement(nodes_el, "node", id=str(n.get("id", "")), label=str(n.get("id", "")))
        ET.SubElement(node_el, "attvalues")  # optional: weight as attribute
    edges_el = ET.SubElement(graph_el, "edges")
    for i, e in enumerate(graph.get("edges") or []):
        ET.SubElement(
            edges_el,
            "edge",
            id=str(i),
            source=str(e.get("source", "")),
            target=str(e.get("target", "")),
            weight=str(float(e.get("weight", 0))),
        )
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True, default_namespace="")


def export_graph_graphml(graph: dict[str, Any], path: str | Path) -> None:
    """
    Export hierarchical graph to GraphML XML.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("graphml")
    root.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
    ET.SubElement(root, "key", id="weight", for="node", attr.name="weight", attr.type="double")
    ET.SubElement(root, "key", id="etype", for="edge", attr.name="edge_type", attr.type="string")
    graph_el = ET.SubElement(root, "graph", id="G", edgedefault="directed")
    for n in graph.get("nodes") or []:
        node_el = ET.SubElement(graph_el, "node", id=str(n.get("id", "")))
        data_el = ET.SubElement(node_el, "data", key="weight")
        data_el.text = str(float(n.get("weight", 0)))
    for i, e in enumerate(graph.get("edges") or []):
        edge_el = ET.SubElement(
            graph_el,
            "edge",
            id=f"e{i}",
            source=str(e.get("source", "")),
            target=str(e.get("target", "")),
        )
        ET.SubElement(edge_el, "data", key="etype").text = str(e.get("edge_type", ""))
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True, default_namespace="")


def plot_activation_heatmap(
    data: list[dict[str, float]] | dict[str, list[float]],
    path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Build data for activation heatmap (e.g. areas or families per segment).
    If path given and matplotlib available, save figure; else return data for external plot.
    data: list of {A2: 0.3, A3: 0.8, ...} per segment, or dict of area_id -> [values].
    """
    if isinstance(data, dict):
        series = data
    else:
        keys = set()
        for row in data:
            keys.update(row.keys())
        keys = sorted(keys)
        series = {k: [row.get(k, 0) for row in data] for k in keys}
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        labels = list(series.keys())
        arr = np.array([series[k] for k in labels], dtype=float)
        if arr.size == 0:
            return {"series": series, "saved": False}
        fig, ax = plt.subplots()
        im = ax.imshow(arr, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("Segment")
        plt.colorbar(im, ax=ax)
        if path is not None:
            plt.savefig(path, bbox_inches="tight")
            plt.close()
            return {"series": series, "saved": True, "path": str(path)}
        plt.close()
        return {"series": series, "saved": False}
    except ImportError:
        return {"series": series, "saved": False, "message": "matplotlib not installed"}


def plot_area_trajectory(
    state_sequence: list[str],
    path: str | Path | None = None,
    area_order: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build/save area trajectory plot (A2 → A3 → A4). state_sequence = ["A2","A3","A4",...].
    If path given and matplotlib available, save figure.
    """
    area_order = area_order or [
        "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12",
    ]
    indices = {a: i for i, a in enumerate(area_order)}
    y = [indices.get(s, 0) for s in state_sequence if s]
    x = list(range(len(y)))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        if not y:
            return {"x": x, "y": y, "labels": state_sequence, "saved": False}
        fig, ax = plt.subplots()
        ax.plot(x, y, marker="o", linestyle="-")
        ax.set_yticks(range(len(area_order)))
        ax.set_yticklabels(area_order)
        ax.set_xlabel("Segment")
        ax.set_ylabel("Area")
        ax.set_title("Session area trajectory")
        if path is not None:
            plt.savefig(path, bbox_inches="tight")
            plt.close()
            return {"x": x, "y": y, "labels": state_sequence, "saved": True, "path": str(path)}
        plt.close()
        return {"x": x, "y": y, "labels": state_sequence, "saved": False}
    except ImportError:
        return {"x": x, "y": y, "labels": state_sequence, "saved": False, "message": "matplotlib not installed"}
