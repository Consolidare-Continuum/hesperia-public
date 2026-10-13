#!/usr/bin/env python3
# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# Grid search over semantic-field parameters; HCI ranking; writes full / best / top_k JSON artifacts.

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

from hesperia.extensions.dynamics.calibration import calibrate_parameter_grid
from hesperia.extensions.dynamics.equations import aggregate_family_to_area, build_identity_family_mapping
from runtime.semantic_field.run_semantic_field import (
    _expand_documents,
    _initial_field_from_config,
    load_json,
    resolve_semantic_field_matrices,
    save_json,
    to_numpy,
)


def _hci_band(hci: float) -> Dict[str, Any]:
    if hci >= 0.85:
        band = "very_strong"
        label = "0.85–1.00 very strong calibration"
    elif hci >= 0.70:
        band = "usable"
        label = "0.70–0.85 usable / strong"
    elif hci >= 0.50:
        band = "weak"
        label = "0.50–0.70 weak / unstable / underfit"
    else:
        band = "poor"
        label = "< 0.50 poor calibration"
    return {"band": band, "label": label, "hspr_calibration_index": round(hci, 6)}


def _best_artifact(best: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "hspr_field_calibration_best_v1",
        "candidate": best.get("candidate"),
        "steps": best.get("steps"),
        "converged_numerical": best.get("converged_numerical"),
        "converged_contradiction": best.get("converged_contradiction"),
        "energy_final": best.get("energy_final"),
        "observables": best.get("observables"),
        "hspr_calibration_index": best.get("hspr_calibration_index"),
        "hspr_components": best.get("hspr_components"),
        "hspr_weights": best.get("hspr_weights"),
        "field_final": best.get("field_final"),
        "area_field_final": best.get("area_field_final"),
        "source_vector": best.get("source_vector"),
    }


def _topk_artifact(rows: list[Dict[str, Any]]) -> Dict[str, Any]:
    slim = []
    for r in rows:
        slim.append(
            {
                "candidate": r.get("candidate"),
                "hspr_calibration_index": r.get("hspr_calibration_index"),
                "hspr_components": r.get("hspr_components"),
                "converged_numerical": r.get("converged_numerical"),
                "converged_contradiction": r.get("converged_contradiction"),
                "energy_final": r.get("energy_final"),
                "steps": r.get("steps"),
            }
        )
    return {"schema": "hspr_field_calibration_topk_v1", "top_k": slim}


def run_field_calibration(config: Dict[str, Any]) -> Dict[str, Any]:
    family_count = int(config["family_count"])
    area_count = int(config.get("area_count", 12))
    families_per_area = int(config.get("families_per_area", 24))
    if family_count != area_count * families_per_area:
        raise ValueError(
            f"family_count ({family_count}) must equal area_count * families_per_area ({area_count}*{families_per_area})"
        )

    adjacency_matrix, resistance_vector, contradiction_matrix, id_map, _prov = (
        resolve_semantic_field_matrices(config)
    )

    if not isinstance(config.get("documents"), list):
        raise ValueError("documents must be a list")
    documents = _expand_documents(config, family_count, family_id_to_index=id_map)

    field_init = _initial_field_from_config(config, family_count)
    grid = config["parameter_grid"]
    if not isinstance(grid, dict):
        raise ValueError("parameter_grid must be an object")

    calibration = calibrate_parameter_grid(
        field_init=field_init,
        adjacency_matrix=adjacency_matrix,
        resistance_vector=resistance_vector,
        contradiction_matrix=contradiction_matrix,
        documents=documents,
        family_count=family_count,
        grid=grid,
        now_t=config.get("time_now"),
        max_steps=int(config.get("max_steps", 50)),
        epsilon=float(config.get("epsilon", 1e-6)),
        tau=float(config.get("tau", 1e-6)),
        clip_mode=bool(config.get("clip_mode", True)),
        hci_weights=config.get("hspr_weights"),
        source_alignment_kappa=float(config.get("source_alignment_kappa", 1.0)),
        top_k=int(config.get("top_k", 10)),
    )

    best = calibration["best"]
    if best is not None:
        mapping = build_identity_family_mapping(
            family_count=family_count,
            families_per_area=families_per_area,
            area_count=area_count,
        )
        ff = np.asarray(best["field_final"], dtype=float)
        area_field = aggregate_family_to_area(ff, mapping, area_count=area_count)
        best["area_field_final"] = np.round(area_field, 6).tolist()

    include_all = bool(config.get("include_all_results", False))
    all_results = calibration["all_results"]
    top_k_list = calibration["top_k"]

    full_out: Dict[str, Any] = {
        "schema": "hspr_field_calibration_v1",
        "spec_ref": "HSPR_CALIBRATION_INDEX_v1",
        "matrices_provenance": _prov,
        "candidate_count": calibration["candidate_count"],
        "best": calibration["best"],
        "top_k": top_k_list,
        "include_all_results": include_all,
    }
    if include_all:
        full_out["all_results"] = all_results
    else:
        full_out["all_results_count"] = len(all_results)
        full_out["all_results_omitted"] = True

    if best is not None:
        full_out["hspr_calibration_index_interpretation"] = _hci_band(float(best["hspr_calibration_index"]))

    return full_out


def write_field_calibration_artifacts(result: Dict[str, Any], out_path: Path) -> tuple[Path, Path, Path]:
    """
    Write full calibration JSON plus *_best.json and *_topk.json beside out_path.
    Returns (main_path, best_path, topk_path).
    """
    stem = out_path.stem
    parent = out_path.parent
    save_json(result, out_path)
    best_path = parent / f"{stem}_best.json"
    topk_path = parent / f"{stem}_topk.json"
    best = result.get("best")
    if best is not None:
        save_json(_best_artifact(best), best_path)
    else:
        save_json({"schema": "hspr_field_calibration_best_v1", "_empty": True}, best_path)
    save_json(_topk_artifact(result.get("top_k") or []), topk_path)
    return out_path, best_path, topk_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HESPERIA semantic field parameter calibration (HCI grid search)")
    parser.add_argument("--config", required=True, help="Path to calibration config JSON")
    parser.add_argument(
        "--output",
        required=True,
        help="Base output path, e.g. out/run_output_e2e_field_calibration.json "
        "(also writes _best.json and _topk.json alongside)",
    )

    args = parser.parse_args()
    out_path = Path(args.output)
    if out_path.suffix.lower() != ".json":
        raise SystemExit("--output must end with .json")

    config = load_json(Path(args.config))
    result = run_field_calibration(config)
    write_field_calibration_artifacts(result, out_path)


if __name__ == "__main__":
    main()
