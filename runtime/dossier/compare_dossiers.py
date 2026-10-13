# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA dossier comparison.
Compares two dossiers and reports structural and interpretation differences.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

# Type for the structured diff returned by compare_dossiers
CompareResult = Dict[str, Any]


def _load_dossier(path: Path | str) -> Dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _list_to_set(val: Any) -> Set[Any]:
    if isinstance(val, list):
        return set(val)
    return set()


def compare_dossiers(file_a: Path | str, file_b: Path | str) -> CompareResult | None:
    """
    Compare two dossier files and return a structured diff.
    Returns None if either file cannot be read.
    Compares: engine_version, policy_mode, document_anomaly, dominant_area_distribution,
    stable_family_core, confidence_profile.mean_confidence.
    """
    a = _load_dossier(file_a)
    b = _load_dossier(file_b)
    if a is None or b is None:
        return None

    meta_a = a.get("meta") or {}
    meta_b = b.get("meta") or {}
    rm_a = meta_a.get("run_manifest") or {}
    rm_b = meta_b.get("run_manifest") or {}
    gs_a = a.get("global_structure") or {}
    gs_b = b.get("global_structure") or {}
    cp_a = gs_a.get("confidence_profile") or {}
    cp_b = gs_b.get("confidence_profile") or {}

    engine_a = meta_a.get("engine_version", "")
    engine_b = meta_b.get("engine_version", "")
    engine_version_changed = engine_a != engine_b

    policy_a = rm_a.get("policy_mode", "")
    policy_b = rm_b.get("policy_mode", "")
    policy_changed = policy_a != policy_b

    anom_a = gs_a.get("document_anomaly")
    anom_b = gs_b.get("document_anomaly")
    if anom_a is not None and anom_b is not None:
        document_anomaly_delta = float(anom_b) - float(anom_a)
    else:
        document_anomaly_delta = None

    dist_a = gs_a.get("dominant_area_distribution") or {}
    dist_b = gs_b.get("dominant_area_distribution") or {}
    area_distribution_delta: Dict[str, Any] = {}
    all_keys = set(dist_a) | set(dist_b)
    for k in sorted(all_keys):
        va = dist_a.get(k)
        vb = dist_b.get(k)
        if va is None and vb is not None:
            area_distribution_delta[k] = {"a": None, "b": float(vb), "delta": float(vb)}
        elif va is not None and vb is None:
            area_distribution_delta[k] = {"a": float(va), "b": None, "delta": -float(va)}
        elif va is not None and vb is not None:
            d = float(vb) - float(va)
            if d != 0:
                area_distribution_delta[k] = {"a": float(va), "b": float(vb), "delta": d}
    # If no deltas, keep empty dict per spec

    family_a = _list_to_set(gs_a.get("stable_family_core"))
    family_b = _list_to_set(gs_b.get("stable_family_core"))
    removed = sorted(family_a - family_b)
    added = sorted(family_b - family_a)
    stable_family_difference: Dict[str, List[Any]] = {"removed": removed, "added": added}

    mean_conf_a = cp_a.get("mean_confidence")
    mean_conf_b = cp_b.get("mean_confidence")
    if mean_conf_a is not None and mean_conf_b is not None:
        mean_confidence_delta = float(mean_conf_b) - float(mean_conf_a)
    else:
        mean_confidence_delta = None

    return {
        "engine_version_changed": engine_version_changed,
        "policy_changed": policy_changed,
        "document_anomaly_delta": document_anomaly_delta,
        "area_distribution_delta": area_distribution_delta,
        "stable_family_difference": stable_family_difference,
        "mean_confidence_delta": mean_confidence_delta,
    }


def _format_delta(d: float | None) -> str:
    if d is None:
        return "N/A"
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.4f}"


def print_compare_result(result: CompareResult | None, file_a: str, file_b: str) -> None:
    """Print human-readable comparison to stdout."""
    if result is None:
        print("Error: could not load one or both dossiers.", file=sys.stderr)
        sys.exit(1)
    print("ENGINE VERSION CHANGED:", result["engine_version_changed"])
    print("POLICY MODE CHANGED:", result["policy_changed"])
    print("DOCUMENT ANOMALY Δ:", _format_delta(result.get("document_anomaly_delta")))
    sf = result.get("stable_family_difference") or {}
    print("STABLE FAMILY DIFFERENCE: {removed:", sf.get("removed", []), ", added:", sf.get("added", []), "}")
    if result.get("mean_confidence_delta") is not None:
        print("MEAN CONFIDENCE Δ:", _format_delta(result["mean_confidence_delta"]))
    ad = result.get("area_distribution_delta") or {}
    if ad:
        print("AREA DISTRIBUTION DELTAS:", ad)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(prog="python -m runtime.dossier.compare_dossiers")
    p.add_argument("file_a", type=Path, help="First dossier JSON")
    p.add_argument("file_b", type=Path, help="Second dossier JSON")
    args = p.parse_args()
    result = compare_dossiers(args.file_a, args.file_b)
    print_compare_result(result, str(args.file_a), str(args.file_b))


if __name__ == "__main__":
    main()
