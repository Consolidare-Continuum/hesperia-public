# HESPERIA — Graph Persistence
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Clinical ActiveGraph: сохранение и загрузка. Форматы: JSON, GraphML.
Neo4j — опционально (интеграция по необходимости).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def save_graph_json(graph: dict[str, Any], path: str | Path) -> None:
    """Сохранить граф (nodes, edges, metadata) в JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)


def load_graph_json(path: str | Path) -> dict[str, Any]:
    """Загрузить граф из JSON."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_graph_graphml(graph: dict[str, Any], path: str | Path) -> None:
    """Сохранить граф в GraphML (совместимо с Neo4j, Gephi)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    kw = ET.SubElement(root, "key", id="weight", **{"for": "node"})
    kw.set("attr.name", "weight")
    kw.set("attr.type", "double")
    ke = ET.SubElement(root, "key", id="etype", **{"for": "edge"})
    ke.set("attr.name", "edge_type")
    ke.set("attr.type", "string")
    g = ET.SubElement(root, "graph", id="G", edgedefault="directed")
    for n in graph.get("nodes") or []:
        nd = ET.SubElement(g, "node", id=str(n.get("id", "")))
        d = ET.SubElement(nd, "data", key="weight")
        d.text = str(float(n.get("weight", 0)))
    for i, e in enumerate(graph.get("edges") or []):
        edge = ET.SubElement(
            g, "edge", id=f"e{i}",
            source=str(e.get("source", "")),
            target=str(e.get("target", "")),
        )
        d = ET.SubElement(edge, "data", key="etype")
        d.text = str(e.get("edge_type", ""))
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(p, encoding="utf-8", xml_declaration=True, default_namespace="")


def load_graph_graphml(path: str | Path) -> dict[str, Any]:
    """Загрузить граф из GraphML (nodes, edges)."""
    p = Path(path)
    if not p.exists():
        return {}
    tree = ET.parse(p)
    root = tree.getroot()
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    nodes = []
    edges = []
    for node in root.findall(".//g:node", ns) or root.findall(".//{http://graphml.graphdrawing.org/xmlns}node"):
        nid = node.get("id", "")
        data = node.find(".//g:data[@key='weight']", ns) or node.find(".//{http://graphml.graphdrawing.org/xmlns}data[@key='weight']")
        w = float(data.text) if data is not None and data.text else 0.0
        nodes.append({"id": nid, "weight": w})
    for edge in root.findall(".//g:edge", ns) or root.findall(".//{http://graphml.graphdrawing.org/xmlns}edge"):
        edges.append({
            "source": edge.get("source", ""),
            "target": edge.get("target", ""),
            "weight": 0.0,
        })
    return {"nodes": nodes, "edges": edges}
