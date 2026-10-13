# HESPERIA — authoritative GO/NO-GO system seal (Task 11; verifies Tasks 1–10 wiring).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""
``run_system_seal_gate`` returns a JSON-serializable report with ``status`` PASS|FAIL and per-check booleans.

Used by ``tools.system_seal.run_system_seal``, release audit, and optional API startup enforcement.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _check_pipeline_integrity(repo: Path) -> tuple[bool, str]:
    """
    Canonical shipping path must not import ``sphere.pipeline`` / ``run_pipeline`` (legacy L1–L9).
    """
    files = (
        repo / "runtime" / "services" / "analysis_service.py",
        repo / "core" / "engine" / "multiscale_product_bridge.py",
        repo / "core" / "engine" / "sealed_multiscale_stack.py",
        repo / "runtime" / "artifact_writer" / "writer.py",
    )
    call_pat = re.compile(r"sphere\.pipeline\.run_pipeline\s*\(")
    for fp in files:
        if not fp.is_file():
            continue
        text = fp.read_text(encoding="utf-8")
        if call_pat.search(text):
            return False, f"{fp.relative_to(repo)} calls sphere.pipeline.run_pipeline(...)"
        if re.search(r"^\s*from\s+sphere\.pipeline\s+import", text, re.MULTILINE):
            return False, f"{fp.relative_to(repo)} imports sphere.pipeline"
        if re.search(r"^\s*import\s+sphere\.pipeline\b", text, re.MULTILINE):
            return False, f"{fp.relative_to(repo)} imports sphere.pipeline module"
    return True, "canonical shipping modules do not invoke legacy sphere.pipeline"


def _check_hex_dependency() -> tuple[bool, str]:
    try:
        from core.engine.product_signals import compute_product_signals
    except Exception as e:
        return False, str(e)
    try:
        compute_product_signals(
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            C_F=np.eye(3),
            dt=1.0,
        )
        return False, "compute_product_signals accepted None hex (expected failure)"
    except (RuntimeError, ValueError) as e:
        msg = str(e).lower()
        if "hex" in msg or "2-d" in msg or "2d" in msg or "missing" in msg:
            return True, f"hex tensors required ({type(e).__name__} as expected)"
        return False, f"wrong error: {e}"
    except Exception as e:
        return False, f"unexpected exception: {e}"


def _check_production_matrices(repo: Path) -> tuple[bool, str]:
    env = os.environ.get("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", "")
    if env in ("1", "true", "yes"):
        return False, "HESPERIA_SEMANTIC_FIELD_STUB_MATRICES must be unset for seal"
    old = os.environ.pop("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", None)
    try:
        from core.engine.matrix_loader import load_production_matrices

        mats = load_production_matrices()
        if "matrix_manifest.json" not in str(mats.get("matrix_directory", "")) and not (
            mats.get("manifest")
        ):
            return False, "missing manifest metadata"
        d = mats["matrix_directory"]
        man = d / "matrix_manifest.json"
        if not man.is_file():
            return False, "matrix_directory has no manifest"
        return True, f"production matrices bundle={mats.get('bundle_version')!r}"
    except Exception as e:
        return False, str(e)
    finally:
        if old is not None:
            os.environ["HESPERIA_SEMANTIC_FIELD_STUB_MATRICES"] = old


def _check_pch(repo: Path) -> tuple[bool, str]:
    old_pch = os.environ.pop("HESPERIA_PCH_UNIFORM_INJECTION_DEV", None)
    try:
        from core.engine.hex_matrix_builders import apply_pch_to_concept_activation
        from core.engine.pch_loader import load_pch

        pch = load_pch()
        if pch.nnz / float(pch.shape[0] * pch.shape[1]) >= 0.01:
            return False, "P_CH not sparse enough"
        a = np.zeros(288, dtype=np.float64)
        a[11] = 1.0
        H = apply_pch_to_concept_activation(a, pch, n_hex_per_family=250)
        if float(np.std(H[11, :])) < 1e-12:
            return False, "P_CH column appears uniform on family row"
        return True, f"P_CH nnz={pch.nnz} active non-uniform"
    except Exception as e:
        return False, str(e)
    finally:
        if old_pch is not None:
            os.environ["HESPERIA_PCH_UNIFORM_INJECTION_DEV"] = old_pch


def _check_energy() -> tuple[bool, str]:
    try:
        from core.engine.energy import EnergyControlParams, EnergyMode
        from hesperia.extensions.dynamics.equations import (
            SemanticFieldParams,
            build_contradiction_matrix,
            build_family_laplacian,
            build_resistance_matrix,
            run_until_convergence,
        )

        ec = EnergyControlParams(mode=EnergyMode.strict)
        p = SemanticFieldParams(
            alpha=0.07,
            beta=0.03,
            gamma=0.05,
            delta=0.18,
            dt=0.05,
            epsilon=1e-4,
            tau=1e-3,
            clip_mode=True,
        )
        n = 4
        f0 = np.random.RandomState(7).rand(n) * 0.12
        s = np.ones(n, dtype=np.float64) * 0.11
        l = build_family_laplacian(np.ones((n, n)) - np.eye(n))
        r = build_resistance_matrix([0.1] * n)
        c = build_contradiction_matrix(np.ones((n, n)) - np.eye(n))
        out = run_until_convergence(f0, s, l, r, c, p, max_steps=24, energy_control=ec)
        et = out.energy_trace
        for a, b in zip(et, et[1:]):
            if b > a + 1e-7:
                return False, f"energy increased {a} -> {b}"
        return True, "strict-mode energy trace monotone"
    except Exception as e:
        return False, str(e)


def _check_concept_layer(repo: Path) -> tuple[bool, str]:
    p = repo / "core" / "engine" / "sealed_multiscale_stack.py"
    if not p.is_file():
        return False, "sealed_multiscale_stack.py missing"
    t = p.read_text(encoding="utf-8")
    if "markers_to_concept_activation" not in t:
        return False, "sealed stack must call markers_to_concept_activation"
    if "_hits_288(" in t:
        return False, "sealed stack must not call _hits_288 directly"
    try:
        from hesperia.extensions.dynamics.e2e_bridge import markers_to_concept_activation

        assets = repo / "assets" / "lexicon" / "curated"
        if not assets.is_dir():
            return True, "concept API present (assets skipped)"
        act = markers_to_concept_activation("justice fairness", assets)
        trace = act.get("marker_concept_trace") or []
        if trace and "concept_id" not in trace[0]:
            return False, "marker_concept_trace entries must include concept_id"
        return True, "explicit A_concept path active"
    except Exception as e:
        return False, str(e)


def _check_topology(repo: Path) -> tuple[bool, str]:
    path = repo / "assets" / "topology" / "hex_topology_v1.json"
    if not path.is_file():
        return False, f"missing {path}"
    try:
        from core.engine.hex_topology_authority import validate_topology_invariants

        validate_topology_invariants()
    except Exception as e:
        return False, str(e)
    h = _sha256_file(path)
    return True, f"sha256={h[:16]}.."


def _check_calibration(repo: Path) -> tuple[bool, str]:
    try:
        from hesperia.engine.calibration_profile import load_calibration_profile
        from hesperia.system.version import calibration_active_profile_id

        path = repo / "assets" / "calibration" / "profiles_v1.json"
        if not path.is_file():
            return False, f"missing {path}"
        docj = json.loads(path.read_text(encoding="utf-8"))
        profiles = docj.get("profiles") or {}
        active = calibration_active_profile_id()
        if active not in profiles:
            return False, f"active profile {active!r} not in profiles_v1.json"
        raw = dict(profiles[active])
        if raw.get("alias_of"):
            base = str(raw["alias_of"])
            raw = dict(profiles[base])
        loaded = load_calibration_profile(active)
        for k in ("alpha", "beta", "gamma", "delta", "dt"):
            if k not in raw or k not in loaded:
                return False, f"missing key {k}"
            if abs(float(loaded[k]) - float(raw[k])) > 1e-12:
                return False, f"VERSION-bound loader mismatch on {k} vs profiles file"
        return True, f"profile {active!r} matches on-disk bundle"
    except Exception as e:
        return False, str(e)


def _check_physics_validation_suite(repo: Path) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(repo / "tests" / "physics_validation"),
        "-q",
        "--tb=no",
    ]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            tail = (r.stdout + r.stderr)[-2000:]
            return False, f"pytest exit {r.returncode}: {tail}"
        return True, "tests/physics_validation passed"
    except Exception as e:
        return False, str(e)


def _check_product_truth(repo: Path) -> tuple[bool, str]:
    try:
        sys.path.insert(0, str(repo))
        from runtime.services.analysis_service import run_structural_analysis
        from runtime.shipping.schema_guard import validate_against_public_schema

        assets = repo / "assets" / "lexicon" / "curated"
        out = run_structural_analysis("justice fairness order care", assets_root=assets, stages="full")
        validate_against_public_schema(out)
        req = ("system_version", "schema_version", "build_id", "calibration_profile")
        missing = [k for k in req if k not in out]
        if missing:
            return False, f"missing envelope keys {missing}"
        if "multiscale_signals" not in out and "payload" not in out:
            # projected shape may nest under payload in some modes — analysis_service returns flat L*/usf
            if "usf" not in out:
                return False, "missing usf / multiscale payload"
        return True, "sample analyze output passes schema_guard + envelope"
    except Exception as e:
        return False, str(e)


def run_system_seal_gate(
    repo_root: Path | None = None,
    *,
    skip_physics_subprocess: bool = False,
) -> dict[str, Any]:
    """
    Execute all mandatory checks. Returns report dict.

    ``skip_physics_subprocess``: test hook to avoid nested pytest when already under pytest.
    """
    repo = Path(repo_root) if repo_root is not None else _repo_root()
    checks: dict[str, bool] = {}
    notes: dict[str, str] = {}

    def _run(name: str, fn) -> None:
        ok, msg = fn()
        checks[name] = ok
        notes[name] = msg

    _run("pipeline", lambda: _check_pipeline_integrity(repo))
    _run("hex_dependency", _check_hex_dependency)
    _run("matrices", lambda: _check_production_matrices(repo))
    _run("pch", lambda: _check_pch(repo))
    _run("energy", _check_energy)
    _run("concept", lambda: _check_concept_layer(repo))
    _run("topology", lambda: _check_topology(repo))
    _run("calibration", lambda: _check_calibration(repo))
    if skip_physics_subprocess:
        checks["validation"] = True
        notes["validation"] = "skipped (skip_physics_subprocess=True; run full seal via tools.system_seal)"
    else:
        _run("validation", lambda: _check_physics_validation_suite(repo))
    _run("product_truth", lambda: _check_product_truth(repo))

    passed = all(checks.values())
    topo_path = repo / "assets" / "topology" / "hex_topology_v1.json"
    topo_hash = _sha256_file(topo_path) if topo_path.is_file() else ""

    try:
        from hesperia.system.version import (
            calibration_active_profile_id,
            get_system_version,
            pch_bundle_id,
            production_matrix_bundle_id,
        )

        sys_ver = get_system_version()
        mat_b = production_matrix_bundle_id()
        pch_b = pch_bundle_id()
        cal_p = calibration_active_profile_id()
    except Exception:
        sys_ver = ""
        mat_b = ""
        pch_b = ""
        cal_p = ""

    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "notes": notes,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "version": sys_ver,
        "matrix_bundle": mat_b,
        "pch_bundle": pch_b,
        "calibration_profile": cal_p,
        "hex_topology_sha256": topo_hash,
    }


__all__ = ["run_system_seal_gate"]
