# HESPERIA — Clinical activation → KME ActiveGraph bridge
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Fusion layer: convert session activation (Dict-A/B output) into graph structure
compatible with KME. Metrics operate on the concept graph only (concept nodes ≈ hex cells).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.domain.active_graph import build_active_graph
from core.domain.models import (
    ConceptHit,
    DomainEdge,
    DomainGraph,
    DomainNode,
    RelationCandidate,
)
from hesperia.engine.calibration.activation_calibration import (
    get_activation_threshold,
    get_area_active_threshold,
    load_calibration_config,
)
from hesperia.ontology.dictB.loader import load_concept_nodes

# Single SoT: assets/specs/canon/activation_calibration.yaml (CHI-B16-02 / CHI-012)
load_calibration_config()

_DICT_B_DIR = Path(__file__).resolve().parents[2] / "ontology" / "dictB"
_RELATIONS_PATH = _DICT_B_DIR / "concept_relations.yaml"


def load_concept_relations(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Загрузить связи между концептами из concept_relations.yaml."""
    p = Path(path) if path is not None else _RELATIONS_PATH
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("relations") or []


def load_domain_graph_from_dict_b(
    nodes_path: Path | str | None = None,
    relations_path: Path | str | None = None,
) -> DomainGraph:
    """
    Построить DomainGraph из Dict-B: узлы — концепты (concept_nodes.yaml),
    рёбра — связи (concept_relations.yaml). Нужен для валидации ActiveGraph в KME.
    """
    nodes_list = load_concept_nodes(nodes_path)
    nodes: dict[str, DomainNode] = {}
    for n in nodes_list:
        if not isinstance(n, dict):
            continue
        cid = n.get("id")
        if cid:
            nodes[str(cid)] = DomainNode(concept_id=str(cid))
    relations = load_concept_relations(relations_path)
    edges: list[DomainEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for r in relations:
        if not isinstance(r, dict):
            continue
        src = r.get("source")
        tgt = r.get("target")
        rel = r.get("relation", "activates")
        if not src or not tgt:
            continue
        src, tgt = str(src), str(tgt)
        if src == tgt:
            continue
        key = (min(src, tgt), max(src, tgt), rel)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            DomainEdge(
                source_concept_id=src,
                target_concept_id=tgt,
                relation_type=str(rel),
            )
        )
    for e in edges:
        if e.source_concept_id not in nodes:
            nodes[e.source_concept_id] = DomainNode(concept_id=e.source_concept_id)
        if e.target_concept_id not in nodes:
            nodes[e.target_concept_id] = DomainNode(concept_id=e.target_concept_id)
    return DomainGraph(nodes=nodes, edges=edges)


def activation_to_hits_and_relations(
    activation_result: dict[str, Any],
    domain_graph: DomainGraph,
) -> tuple[list[ConceptHit], list[RelationCandidate]]:
    """
    Преобразовать результат активации в hits и relations для KME.
    Только концепты с score > 0; hit_count отражает силу активации.
    Relations — рёбра из domain (Dict-B), оба конца в активном множестве.
    """
    concepts = (activation_result or {}).get("concepts") or {}
    active: set[str] = set()
    for cid, score in concepts.items():
        try:
            s = float(score)
        except (TypeError, ValueError):
            continue
        if s > 0 and cid in domain_graph.nodes:
            active.add(str(cid))
    hits: list[ConceptHit] = []
    for cid in active:
        score = float(concepts.get(cid, 0))
        hit_count = max(1, int(round(score * 100)))
        for i in range(hit_count):
            hits.append(ConceptHit(concept_id=cid, token_index=i))
    relations: list[RelationCandidate] = []
    for e in domain_graph.edges:
        if e.source_concept_id in active and e.target_concept_id in active:
            relations.append(
                RelationCandidate(
                    concept_a=e.source_concept_id,
                    concept_b=e.target_concept_id,
                    relation_type=e.relation_type,
                )
            )
    return hits, relations


def build_clinical_active_graph(
    activation_result: dict[str, Any],
    domain_graph: DomainGraph | None = None,
) -> "ActiveGraph":
    """
    Построить ActiveGraph для KME из результата клинической активации.
    Узлы — только концепты (concept_id, hit_count из score).
    Рёбра — связи Dict-B между активными концептами.
    Метрики KME работают по графу концептов (concept nodes ≈ hex cells).
    """
    from core.domain.models import ActiveGraph

    if domain_graph is None:
        domain_graph = load_domain_graph_from_dict_b()
    hits, relations = activation_to_hits_and_relations(activation_result, domain_graph)
    return build_active_graph(hits, relations, domain_graph)


def run_kme_from_activation(
    activation_result: dict[str, Any],
    source_id: str = "session",
    domain_graph: DomainGraph | None = None,
    domain_release: str = "",
) -> "MetricReport":
    """
    Полный прогон KME по результату активации сессии:
    Clinical ActiveGraph → Primitives → Derived → Fingerprint → MetricReport.
    """
    from core.domain.derived_metrics import compute_derived_metrics
    from core.domain.extractor import extract_constants
    from core.domain.fingerprint import build_fingerprint
    from core.domain.models import MetricReport
    from core.domain.primitive_metrics import compute_primitives

    if domain_graph is None:
        domain_graph = load_domain_graph_from_dict_b()
    domain_constants = extract_constants(domain_graph)
    active_graph = build_clinical_active_graph(activation_result, domain_graph)
    primitives = compute_primitives(active_graph, domain_constants)
    derived = compute_derived_metrics(primitives)
    fingerprint = build_fingerprint(
        primitives,
        derived,
        domain_release=domain_release,
        source_id=source_id,
    )
    from hesperia.extensions.triz.kme_bridge import run_triz_for_kme

    topo: dict[str, Any] | None = None
    c2a = activation_result.get("concept_to_area")
    c2f = activation_result.get("concept_to_family")
    if isinstance(c2a, dict) and isinstance(c2f, dict):

        def _ival(x: Any) -> int | None:
            try:
                return int(x)
            except (TypeError, ValueError):
                try:
                    return int(float(x))
                except (TypeError, ValueError):
                    return None

        ca = {str(k): v for k, v in c2a.items() if str(k) in active_graph.nodes and _ival(v) is not None}
        cf = {str(k): v for k, v in c2f.items() if str(k) in active_graph.nodes and _ival(v) is not None}
        ca = {k: _ival(v) for k, v in ca.items()}
        cf = {k: _ival(v) for k, v in cf.items()}
        if ca and cf:
            topo = {"concept_to_area": dict(sorted(ca.items())), "concept_to_family": dict(sorted(cf.items()))}
    triz_signals = run_triz_for_kme(active_graph, topo)
    return MetricReport(
        source_id=source_id,
        primitive_map=fingerprint.primitive_map,
        derived_map=fingerprint.derived_map,
        fingerprint=fingerprint,
        triz_signals=triz_signals,
    )


# ---------------------------------------------------------------------------
# LEVEL 14 — Hierarchical Clinical ActiveGraph (concept + family + area)
# ---------------------------------------------------------------------------

def __getattr__(name: str):
    """Lazy aliases — live SoT is activation_calibration getters (CHI-B16-02)."""
    if name == "ACTIVATION_THRESHOLD":
        return get_activation_threshold()
    if name == "AREA_ACTIVE_THRESHOLD":
        return get_area_active_threshold()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Graph sparsification (avoid dense graphs for KME)
TOP_K_CONCEPTS = 60
TOP_K_FAMILIES = 30
MIN_EDGE_WEIGHT = 0.05

_SPEC_DIR = Path(__file__).resolve().parents[3] / "spec"


def load_concept_relation_weights(path: Path | str | None = None) -> dict[str, float]:
    """Load spec/concept_relation_weights.yaml. Relation type -> weight (opposes negative for CI)."""
    p = Path(path) if path is not None else _SPEC_DIR / "concept_relation_weights.yaml"
    if not p.exists():
        return {
            "activates": 1.0,
            "co_occurs_with": 0.7,
            "expresses": 0.6,
            "defends_against": 0.5,
            "opposes": -0.6,
            "observed_in": 0.5,
            "part_of": 0.6,
            "is_a": 0.6,
        }
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    rw = data.get("relation_weights") or {}
    default = float(data.get("default_weight", 0.5))
    return {str(k): float(v) for k, v in rw.items()} if rw else {"activates": 1.0}


def load_clinical_relation_sources(
    concept_nodes_path: Path | str | None = None,
    concept_relations_path: Path | str | None = None,
    family_embedding_path: Path | str | None = None,
    concept_relation_weights_path: Path | str | None = None,
) -> dict[str, Any]:
    """Load all ontology resources needed by the hierarchical bridge."""
    return {
        "concept_nodes": load_concept_nodes(concept_nodes_path),
        "concept_relations": load_concept_relations(concept_relations_path),
        "family_embedding": _load_family_embedding_yaml(family_embedding_path),
        "area_structure": _load_area_structure_yaml(),
        "concept_relation_weights": load_concept_relation_weights(concept_relation_weights_path),
    }


def _load_family_embedding_yaml(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else _SPEC_DIR / "family_embedding_tfp.yaml"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _load_area_structure_yaml() -> dict[str, Any]:
    p = _SPEC_DIR / "area_structure_tfp.yaml"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _concept_to_area_family(cid: str) -> tuple[str, str]:
    """Parse B_A3_F1_001 -> (A3, A3_F1)."""
    parts = cid.split("_")
    if len(parts) >= 3 and parts[0] == "B" and parts[1].startswith("A"):
        area = parts[1]
        fam = parts[2]
        return area, f"{area}_{fam}"
    return "", ""


def build_active_concept_nodes(
    concept_scores: dict[str, float],
    concept_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build concept-level nodes from activation scores (calibration activation_threshold)."""
    out: list[dict[str, Any]] = []
    by_id = {n.get("id"): n for n in concept_nodes if isinstance(n, dict) and n.get("id")}
    for cid, w in (concept_scores or {}).items():
        if float(w) < get_activation_threshold():
            continue
        area, family_id = _concept_to_area_family(cid)
        node_info = by_id.get(cid) or {}
        out.append({
            "id": cid,
            "node_type": "concept",
            "weight": round(float(w), 4),
            "area_id": area,
            "family_id": family_id,
            "label": node_info.get("label", ""),
            "metadata": {},
        })
    return sorted(out, key=lambda n: n["id"])


def build_active_family_nodes(family_scores: dict[str, float]) -> list[dict[str, Any]]:
    """Build family-level nodes (calibration activation_threshold)."""
    out: list[dict[str, Any]] = []
    for fid, w in (family_scores or {}).items():
        if float(w) < get_activation_threshold():
            continue
        if "_" in fid and fid.split("_")[0].startswith("A"):
            area_id = fid.split("_")[0]
        else:
            area_id = ""
        out.append({
            "id": fid,
            "node_type": "family",
            "weight": round(float(w), 4),
            "area_id": area_id,
            "family_id": fid,
            "label": "",
            "metadata": {},
        })
    return sorted(out, key=lambda n: n["id"])


def build_active_area_nodes(area_scores: dict[str, float]) -> list[dict[str, Any]]:
    """Build area-level nodes (calibration activation_threshold)."""
    out: list[dict[str, Any]] = []
    for aid, w in (area_scores or {}).items():
        if float(w) < get_activation_threshold():
            continue
        out.append({
            "id": aid,
            "node_type": "area",
            "weight": round(float(w), 4),
            "area_id": aid,
            "family_id": "",
            "label": "",
            "metadata": {},
        })
    return sorted(out, key=lambda n: n["id"])


def build_hierarchical_edges(
    concept_scores: dict[str, float],
    family_scores: dict[str, float],
    area_scores: dict[str, float],
) -> list[dict[str, Any]]:
    """Create concept→family (belongs_to_family) and family→area (belongs_to_area) edges."""
    edges: list[dict[str, Any]] = []
    for cid, w in (concept_scores or {}).items():
        if float(w) < get_activation_threshold():
            continue
        _, family_id = _concept_to_area_family(cid)
        if family_id and (family_scores or {}).get(family_id, 0) >= get_activation_threshold():
            edges.append({
                "source": cid,
                "target": family_id,
                "edge_type": "belongs_to_family",
                "weight": round(float(w), 4),
            })
    for fid, w in (family_scores or {}).items():
        if float(w) < get_activation_threshold():
            continue
        if "_" in fid:
            area_id = fid.split("_")[0]
            if (area_scores or {}).get(area_id, 0) >= get_activation_threshold():
                edges.append({
                    "source": fid,
                    "target": area_id,
                    "edge_type": "belongs_to_area",
                    "weight": round(float(w), 4),
                })
    return edges


def build_concept_relation_edges(
    concept_scores: dict[str, float],
    concept_relations: list[dict[str, Any]],
    pilot_concept_ids: set[str] | None = None,
    relation_weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Create concept↔concept edges from concept_relations. Weight: base * abs(relation_weight); relation_weights from spec/concept_relation_weights.yaml."""
    edges: list[dict[str, Any]] = []
    rw = relation_weights or {}
    default_mult = 0.5
    for r in concept_relations or []:
        if not isinstance(r, dict):
            continue
        src = r.get("source")
        tgt = r.get("target")
        rel = r.get("relation", "activates")
        if not src or not tgt or src == tgt:
            continue
        ws = float(concept_scores.get(src, 0) or 0)
        wt = float(concept_scores.get(tgt, 0) or 0)
        if ws < get_activation_threshold() and wt < get_activation_threshold():
            continue
        if ws >= get_activation_threshold() and wt >= get_activation_threshold():
            base = min(ws, wt)
        else:
            base = max(ws, wt) * 0.5
        mult = abs(float(rw.get(rel, default_mult)))
        weight = base * mult
        if weight < get_activation_threshold():
            continue
        edges.append({
            "source": src,
            "target": tgt,
            "edge_type": rel,
            "weight": round(weight, 4),
        })
    return edges


def build_family_topology_edges(
    family_scores: dict[str, float],
    family_embedding: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create intra_area_adjacent (zone neighbors) and bridge edges. Weight: min(source, target)."""
    from sphere.topology.family_embedding import (
        ZONE_KEYS,
        get_area_zones,
        get_composite_family_id,
        get_bridges,
    )
    edges: list[dict[str, Any]] = []
    zone_pairs = [
        ("center", "inner_ring"),
        ("inner_ring", "middle_ring"),
        ("middle_ring", "outer_ring"),
    ]
    for area_id, area_data in (family_embedding or {}).items():
        if not isinstance(area_data, dict):
            continue
        if not (area_id.startswith("A") and len(area_id) >= 2 and (len(area_id) == 2 or area_id[1:].isdigit())):
            continue
        if "center" not in area_data and "inner_ring" not in area_data:
            continue
        zones = get_area_zones(family_embedding, area_id)
        for z1, z2 in zone_pairs:
            for local1 in zones.get(z1) or []:
                for local2 in zones.get(z2) or []:
                    f1 = get_composite_family_id(area_id, local1)
                    f2 = get_composite_family_id(area_id, local2)
                    w1 = (family_scores or {}).get(f1, 0) or 0
                    w2 = (family_scores or {}).get(f2, 0) or 0
                    if w1 >= get_activation_threshold() and w2 >= get_activation_threshold():
                        edges.append({
                            "source": f1,
                            "target": f2,
                            "edge_type": "intra_area_adjacent",
                            "weight": round(min(w1, w2), 4),
                        })
    for b in get_bridges(family_embedding):
        fr = b.get("from")
        to = b.get("to")
        if not fr or not to:
            continue
        w1 = (family_scores or {}).get(fr, 0) or 0
        w2 = (family_scores or {}).get(to, 0) or 0
        if w1 >= get_activation_threshold() and w2 >= get_activation_threshold():
            edges.append({
                "source": fr,
                "target": to,
                "edge_type": "bridge",
                "weight": round(min(w1, w2), 4),
            })
    return edges


def build_area_topology_edges(
    area_scores: dict[str, float],
    area_structure: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create area_adjacent edges from area topology. Only areas with score >= get_area_active_threshold()."""
    edges: list[dict[str, Any]] = []
    areas_list = (area_structure or {}).get("areas") or []
    area_index_to_id: dict[int, str] = {}
    for a in areas_list:
        if not isinstance(a, dict):
            continue
        aid = a.get("area_id")
        idx = a.get("area_index")
        if aid is not None and idx is not None:
            area_index_to_id[int(idx)] = str(aid)
    for a in areas_list:
        if not isinstance(a, dict):
            continue
        aid = a.get("area_id")
        neighbors = a.get("area_neighbors") or []
        wa = float((area_scores or {}).get(str(aid), 0) or 0)
        if wa < get_area_active_threshold():
            continue
        for ni in neighbors:
            nid = area_index_to_id.get(int(ni), "")
            if not nid:
                continue
            wn = float((area_scores or {}).get(nid, 0) or 0)
            if wn < get_area_active_threshold():
                continue
            edges.append({
                "source": str(aid),
                "target": nid,
                "edge_type": "area_adjacent",
                "weight": round(min(wa, wn), 4),
            })
    return edges


def _sparsify_scores(scores: dict[str, float], top_k: int) -> dict[str, float]:
    """Keep only top_k entries by score (descending)."""
    if not scores or top_k <= 0:
        return dict(scores)
    items = sorted(scores.items(), key=lambda x: -float(x[1]))
    return dict(items[:top_k])


def _merge_edges(edge_lists: list[list[dict[str, Any]]], min_edge_weight: float = 0.0) -> list[dict[str, Any]]:
    """Merge edges: same (source, target, edge_type) -> keep max weight. Drop edges below min_edge_weight. Sort."""
    key_to_weight: dict[tuple[str, str, str], float] = {}
    for lst in edge_lists:
        for e in lst:
            src = e.get("source")
            tgt = e.get("target")
            typ = e.get("edge_type", "")
            w = float(e.get("weight", 0) or 0)
            if not src or not tgt or w < min_edge_weight:
                continue
            key = (src, tgt, typ)
            key_to_weight[key] = max(key_to_weight.get(key, 0), w)
    out = [
        {"source": s, "target": t, "edge_type": typ, "weight": round(w, 4)}
        for (s, t, typ), w in key_to_weight.items()
        if w >= min_edge_weight
    ]
    return sorted(out, key=lambda x: (x["source"], x["target"], x["edge_type"]))


def build_clinical_active_graph_hierarchical(
    activation_result: dict[str, Any],
    concept_nodes_path: Path | str | None = None,
    concept_relations_path: Path | str | None = None,
    family_embedding_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Build the full Clinical ActiveGraph: concept + family + area nodes and all edge types.
    Deterministic: nodes sorted by id, edges merged by (source, target, edge_type) with max weight, then sorted.
    Returns dict with nodes, edges, metadata (KME-compatible structure for inspection/visualization).
    """
    activation_result = activation_result or {}
    concept_scores = _sparsify_scores(activation_result.get("concepts") or {}, TOP_K_CONCEPTS)
    family_scores = _sparsify_scores(activation_result.get("families") or {}, TOP_K_FAMILIES)
    area_scores = activation_result.get("areas") or {}

    sources = load_clinical_relation_sources(
        concept_nodes_path=concept_nodes_path,
        concept_relations_path=concept_relations_path,
        family_embedding_path=family_embedding_path,
    )
    concept_nodes_list = sources.get("concept_nodes") or []
    concept_relations = sources.get("concept_relations") or []
    family_embedding = sources.get("family_embedding") or {}
    area_structure = sources.get("area_structure") or {}
    relation_weights = sources.get("concept_relation_weights") or {}

    pilot_concept_ids = {n.get("id") for n in concept_nodes_list if isinstance(n, dict) and n.get("id")}

    nodes = (
        build_active_concept_nodes(concept_scores, concept_nodes_list)
        + build_active_family_nodes(family_scores)
        + build_active_area_nodes(area_scores)
    )
    nodes = sorted(nodes, key=lambda n: n["id"])

    all_edges = _merge_edges([
        build_hierarchical_edges(concept_scores, family_scores, area_scores),
        build_concept_relation_edges(concept_scores, concept_relations, pilot_concept_ids, relation_weights=relation_weights),
        build_family_topology_edges(family_scores, family_embedding),
        build_area_topology_edges(area_scores, area_structure),
    ], min_edge_weight=MIN_EDGE_WEIGHT)

    return {
        "nodes": nodes,
        "edges": all_edges,
        "metadata": {
            "source": "clinical_bridge",
            "node_count": len(nodes),
            "edge_count": len(all_edges),
            "levels": ["concept", "family", "area"],
        },
    }


def analyze_session_to_kme_graph(
    text: str,
    embedding: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Pipeline: text → analyze_session (with optional propagation) → build_clinical_active_graph_hierarchical.
    Returns the hierarchical graph (nodes, edges, metadata).
    """
    from hesperia.nlp.session_parser import analyze_session

    if embedding is None:
        try:
            from sphere.topology.family_embedding import load_family_embedding_tfp
            embedding = load_family_embedding_tfp()
        except Exception:
            embedding = {}
    activation = analyze_session(text, embedding=embedding, **kwargs)
    return build_clinical_active_graph_hierarchical(activation)


def run_session_kme_pipeline(
    text: str,
    source_id: str = "session",
    embedding: dict[str, Any] | None = None,
    **kwargs: Any,
) -> "MetricReport":
    """
    Pipeline: text → analyze_session (with propagation) → run_kme_from_activation.
    Returns KME MetricReport (primitives, derived, fingerprint).
    """
    from hesperia.nlp.session_parser import analyze_session

    if embedding is None:
        try:
            from sphere.topology.family_embedding import load_family_embedding_tfp
            embedding = load_family_embedding_tfp()
        except Exception:
            embedding = {}
    activation = analyze_session(text, embedding=embedding, **kwargs)
    return run_kme_from_activation(activation, source_id=source_id)
