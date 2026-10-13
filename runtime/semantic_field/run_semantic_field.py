#!/usr/bin/env python3
# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# Executes hesperia.extensions.dynamics.equations from explicit or shortcut config.
# Full matrices may be supplied; for 288 families use adjacency_mode / contradiction_zero
# to avoid huge JSON. Optional ontology block → matrix_builders (FIELD_MATRIX_BUILDERS_v1).

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np

_HESPERIA_ROOT = Path(__file__).resolve().parents[2]
if str(_HESPERIA_ROOT) not in sys.path:
    sys.path.insert(0, str(_HESPERIA_ROOT))

from hesperia.extensions.dynamics import matrix_builders as _mb
from hesperia.extensions.dynamics.equations import (
    SemanticFieldParams,
    aggregate_family_to_area,
    aggregate_sources_with_params,
    build_contradiction_matrix,
    build_family_laplacian,
    build_identity_family_mapping,
    build_resistance_matrix,
    run_until_convergence,
)


# -------------------------------------------------------------
# utilities
# -------------------------------------------------------------


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def to_numpy(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _adjacency_from_config(config: Dict[str, Any], fc: int) -> np.ndarray:
    if "adjacency_matrix" in config:
        adj = to_numpy(config["adjacency_matrix"])
        if adj.shape != (fc, fc):
            raise ValueError(f"adjacency_matrix must be ({fc},{fc}), got {adj.shape}")
        return adj
    mode = config.get("adjacency_mode")
    if mode == "canonical_ring":
        w = np.zeros((fc, fc), dtype=float)
        for i in range(fc):
            w[i, (i - 1) % fc] = 1.0
            w[i, (i + 1) % fc] = 1.0
        return w
    raise ValueError(
        'Set "adjacency_matrix" (fc×fc) or adjacency_mode: "canonical_ring" for ring neighbors.'
    )


def _resistance_from_config(config: Dict[str, Any], fc: int) -> np.ndarray:
    r = config["resistance_vector"]
    if isinstance(r, (int, float)):
        return np.full(fc, float(r), dtype=float)
    arr = to_numpy(r).ravel()
    if arr.size == 1:
        return np.full(fc, float(arr[0]), dtype=float)
    if arr.shape[0] != fc:
        raise ValueError(f"resistance_vector length must be 1 or {fc}, got {arr.shape[0]}")
    return arr


def _expand_documents(
    config: Dict[str, Any],
    fc: int,
    *,
    family_id_to_index: Dict[str, int] | None = None,
) -> list[Dict[str, Any]]:
    """source_vector | source_family_index | source_family_id (ontology ids)."""
    raw = config["documents"]
    out: list[Dict[str, Any]] = []
    for idx, d in enumerate(raw):
        if not isinstance(d, dict):
            raise ValueError(f"documents[{idx}] must be an object")
        if "source_vector" in d:
            out.append(dict(d))
            continue
        if "source_family_id" in d:
            if not family_id_to_index:
                raise ValueError(
                    f"documents[{idx}].source_family_id requires config.ontology.family_ids"
                )
            fid = str(d["source_family_id"])
            if fid not in family_id_to_index:
                raise ValueError(f"documents[{idx}]: unknown source_family_id {fid!r}")
            j = family_id_to_index[fid]
            v = np.zeros(fc, dtype=float)
            v[j] = float(d.get("source_strength", 1.0))
            merged = {
                k: v for k, v in d.items() if k not in ("source_family_id", "source_strength")
            }
            merged["source_vector"] = v.tolist()
            out.append(merged)
            continue
        if "source_family_index" in d:
            v = np.zeros(fc, dtype=float)
            j = int(d["source_family_index"])
            if not (0 <= j < fc):
                raise ValueError(f"documents[{idx}].source_family_index out of range")
            v[j] = float(d.get("source_strength", 1.0))
            merged = {k: v for k, v in d.items() if k not in ("source_family_index", "source_strength")}
            merged["source_vector"] = v.tolist()
            out.append(merged)
            continue
        raise ValueError(
            f"documents[{idx}]: need source_vector, source_family_index, or source_family_id"
        )
    return out


def resolve_semantic_field_matrices(
    config: Dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, int] | None, str]:
    """
    Returns (adjacency_W, resistance_vector, contradiction_C_canonical, family_id_index|None, provenance).
    provenance: \"ontology\" | \"config\".
    """
    fc = int(config["family_count"])
    ont = config.get("ontology")
    if ont is not None:
        if not isinstance(ont, dict):
            raise ValueError("ontology must be an object")
        family_ids = [str(x) for x in (ont.get("family_ids") or [])]
        if len(family_ids) != fc:
            raise ValueError(
                f"len(ontology.family_ids) ({len(family_ids)}) must equal family_count ({fc})"
            )
        rels: list[tuple[str, str]] = []
        for row in ont.get("relations") or []:
            if len(row) >= 2:
                rels.append((str(row[0]), str(row[1])))
        cons: list[tuple[str, str, float]] = []
        for row in ont.get("contradictions") or []:
            if len(row) >= 3:
                cons.append((str(row[0]), str(row[1]), float(row[2])))
        priors = {str(k): float(v) for k, v in (ont.get("resistance_priors") or {}).items()}
        default_r = float(ont.get("resistance_default", 0.1))
        w = _mb.build_family_adjacency_matrix(family_ids, rels)
        c0 = _mb.build_contradiction_matrix(family_ids, cons)
        np.fill_diagonal(c0, 0.0)
        c = build_contradiction_matrix(np.asarray(c0, dtype=float))
        r = _mb.build_resistance_vector(family_ids, priors, default_r)
        id_map = _mb.build_family_index(family_ids)
        return w, r, c, id_map, "ontology"

    adj = _adjacency_from_config(config, fc)
    res = _resistance_from_config(config, fc)
    c0 = _contradiction_from_config(config, fc)
    c = build_contradiction_matrix(np.asarray(c0, dtype=float))
    return adj, res, c, None, "config"


def _initial_field_from_config(config: Dict[str, Any], fc: int) -> np.ndarray:
    if config.get("initial_mode") == "uniform":
        return np.full(fc, 1.0 / fc, dtype=float)
    if "initial_field" not in config or config["initial_field"] is None:
        raise ValueError('Provide initial_field (length fc) or initial_mode: "uniform"')
    field_init = to_numpy(config["initial_field"]).ravel()
    if field_init.shape[0] != fc:
        raise ValueError(f"initial_field length must be {fc}, got {field_init.shape[0]}")
    return field_init


def _contradiction_from_config(config: Dict[str, Any], fc: int) -> np.ndarray:
    if config.get("contradiction_zero") is True and "contradiction_matrix" not in config:
        return np.zeros((fc, fc), dtype=float)
    if "contradiction_matrix" not in config:
        raise ValueError('Provide contradiction_matrix (fc×fc) or "contradiction_zero": true')
    c = to_numpy(config["contradiction_matrix"])
    if c.shape != (fc, fc):
        raise ValueError(f"contradiction_matrix must be ({fc},{fc}), got {c.shape}")
    return c


# -------------------------------------------------------------
# core runner
# -------------------------------------------------------------


def run_semantic_field(config: Dict[str, Any]) -> Dict[str, Any]:
    family_count = int(config["family_count"])

    adjacency, resistance, c_mat, id_map, mat_prov = resolve_semantic_field_matrices(config)
    laplacian = build_family_laplacian(adjacency)
    r_mat = build_resistance_matrix(resistance)

    params = SemanticFieldParams(
        alpha=float(config["alpha"]),
        beta=float(config["beta"]),
        gamma=float(config["gamma"]),
        delta=float(config["delta"]),
        mu=float(config.get("mu", 0.0)),
        dt=float(config.get("dt", 1.0)),
        epsilon=float(config.get("epsilon", 1e-6)),
        tau=float(config.get("tau", 1e-6)),
        clip_mode=bool(config.get("clip_mode", True)),
    )

    field_init = _initial_field_from_config(config, family_count)

    if not isinstance(config.get("documents"), list):
        raise ValueError("documents must be a list")

    documents = _expand_documents(config, family_count, family_id_to_index=id_map)

    source_vector = aggregate_sources_with_params(
        documents,
        family_count=family_count,
        params=params,
        now_t=config.get("time_now"),
    )

    outcome = run_until_convergence(
        field_init,
        source_vector,
        laplacian,
        r_mat,
        c_mat,
        params,
        max_steps=int(config.get("max_steps", 50)),
    )
    final_field, timeline = outcome

    fpa = int(config.get("families_per_area", 24))
    ac = int(config.get("area_count", 12))
    if family_count != ac * fpa:
        raise ValueError(f"family_count ({family_count}) must equal area_count * families_per_area ({ac}*{fpa})")

    mapping = build_identity_family_mapping(
        family_count=family_count,
        families_per_area=fpa,
        area_count=ac,
    )

    area_field = aggregate_family_to_area(
        final_field,
        mapping,
        area_count=ac,
    )

    timeline_json = [t.to_json_dict() for t in timeline]

    energy_prev = [round(float(t.result.energy_prev), 6) for t in timeline]
    energy_next = [round(float(t.result.energy_next), 6) for t in timeline]

    result: Dict[str, Any] = {
        "matrices_provenance": mat_prov,
        "family_field_final": np.round(final_field, 6).tolist(),
        "area_field_final": np.round(area_field, 6).tolist(),
        "steps": len(timeline_json),
        "timeline": timeline_json,
        "energy_prev_trajectory": energy_prev,
        "energy_next_trajectory": energy_next,
        "energy_trace": [round(float(x), 8) for x in outcome.energy_trace],
        "convergence_flag": outcome.convergence_flag,
        "steps_to_convergence": outcome.steps_to_convergence,
    }
    if id_map is not None:
        result["family_id_index"] = dict(sorted(id_map.items(), key=lambda x: x[1]))

    return result


# -------------------------------------------------------------
# CLI
# -------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HESPERIA semantic field dynamics")
    parser.add_argument("--config", required=True, help="JSON config path")
    parser.add_argument("--output", required=True, help="JSON output path")

    args = parser.parse_args()

    config = load_json(Path(args.config))
    result = run_semantic_field(config)

    save_json(result, Path(args.output))


if __name__ == "__main__":
    main()
