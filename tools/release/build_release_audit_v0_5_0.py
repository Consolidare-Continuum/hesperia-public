#!/usr/bin/env python3
# HESPERIA — Task 5: sealed release audit package under release/v0.5.0/
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root):
#   python3 tools/release/build_release_audit_v0_5_0.py
#   python3 tools/release/build_release_audit_v0_5_0.py --quick
#
# Exit codes: 0 = all gates pass (may tag). 1 = gate failure (do not tag). 2 = determinism failure.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_RELEASE_DIR = _REPO / "release" / "v0.5.0"
_SCHEMA_SRC = _REPO / "schemas" / "public" / "public_output_schema.json"
_CAPS_SRC = _REPO / "hesperia" / "system" / "capabilities.yaml"
_VERSION_YAML = _REPO / "VERSION.yaml"
_PYPROJECT = _REPO / "pyproject.toml"
_FIXTURE_INPUT = _REPO / "tests" / "fixtures" / "release_v0_5_0" / "canonical_input.txt"
_EXTENSION_STATUS = _REPO / "EXTENSION_STATUS.yaml"

# Tier-1 canonical specs — all must exist for seal (Task 5 Part F).
TIER1_SPEC_PATHS: tuple[str, ...] = (
    "specs/schema/public_output_schema.md",
    "specs/system/versioning_and_governance.md",
    "specs/core/system_architecture.md",
    "specs/canon/hex_microphysics_canon.md",
    "specs/canon/semantic_field_canon.md",
    "specs/canon/hex_family_bridge.md",
    "specs/canon/product_signal_layer.md",
    "specs/canon/hspr_calibration_index.md",
    "specs/core/family_aggregation.md",
    "specs/core/area_aggregation.md",
    "specs/dynamics/HESPERIA_DYNAMICS_CALIBRATION_SPEC_v0_1.md",
    "specs/triz/contradiction_engine.md",
    "docs/TOPOLOGY_INVARIANTS.md",
)

ALLOWED_SHIPPING_ROUTES = frozenset(
    {
        "GET /health",
        "POST /analyze",
        "POST /compare",
        "POST /batch",
        "POST /batch-analyze",
    }
)


def _round_floats(obj: object, ndigits: int = 10) -> object:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x, ndigits) for x in obj]
    return obj


def _git_commit() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=_REPO,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _git_dirty() -> bool:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=_REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(r.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_canonical_input(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Canonical fixture missing: {path}")
    return path.read_text(encoding="utf-8").strip()


def _apply_release_build_env(commit: str, ts: str) -> None:
    os.environ["HESPERIA_GIT_COMMIT"] = commit
    os.environ["HESPERIA_BUILD_TIMESTAMP"] = ts
    try:
        from hesperia.system import version as vmod

        vmod.load_version_document.cache_clear()
    except Exception:
        pass


def _canonical_analyze_dict(text: str) -> dict[str, Any]:
    sys.path.insert(0, str(_REPO))
    from runtime.services.analysis_service import run_structural_analysis

    assets = _REPO / "assets" / "lexicon" / "curated"
    raw = run_structural_analysis(text, assets_root=assets, stages="full")
    return _round_floats(raw, 10)  # type: ignore[return-value]


def _determinism_triplicate(text: str) -> tuple[bool, str, list[str], list[bytes]]:
    blobs: list[bytes] = []
    hashes: list[str] = []
    for _ in range(3):
        payload = _canonical_analyze_dict(text)
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        blobs.append(blob)
        hashes.append(_sha256_bytes(blob))
    ok = len(set(hashes)) == 1
    return ok, hashes[0] if ok else hashes[0], hashes, blobs


def _json_schema_validate(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema package not installed — run pip install -r requirements/runtime.txt"]
    errs: list[str] = []
    v = Draft202012Validator(schema)
    for e in v.iter_errors(instance):
        errs.append(f"{e.json_path}: {e.message}")
    return errs


def _envelope_minimum_check(d: dict[str, Any]) -> list[str]:
    """Hard gates aligned with VERSION.yaml public envelope."""
    req = ("system_version", "schema_version", "build_id", "calibration_profile")
    missing = [k for k in req if k not in d]
    return [f"missing_envelope_field:{k}" for k in missing]


def _leak_scan_public_schema_guard(obj: dict[str, Any] | list[Any]) -> None:
    from runtime.shipping.schema_guard import validate_against_public_schema

    validate_against_public_schema(obj)


def _shipping_routes() -> list[str]:
    sys.path.insert(0, str(_REPO))
    from runtime.shipping.api_main import create_app

    app = create_app()
    out: list[str] = []
    for route in app.routes:
        p = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if p and methods:
            for m in sorted(methods - {"HEAD"}):
                out.append(f"{m} {p}")
        elif p:
            out.append(str(p))
    return sorted(set(out))


def _build_specs_index() -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    for base in (_REPO / "specs", _REPO / "spec"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(_REPO).as_posix()
            entries.append({"path": rel, "sha256": _sha256_file(p)})
    return {"generated_utc": datetime.now(timezone.utc).isoformat(), "spec_files": entries}


def _run_pytest(quick: bool) -> dict[str, Any]:
    if quick:
        args = [
            sys.executable,
            "-m",
            "pytest",
            "tests/engine/test_projection_product_surface.py",
            "tests/test_sealed_runtime_regression.py",
            "tests/test_release_v0_5_0_audit_package.py",
            "-q",
            "--tb=no",
        ]
    else:
        args = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"]
    started = datetime.now(timezone.utc).isoformat()
    r = subprocess.run(args, cwd=_REPO, capture_output=True, text=True)
    tail = (r.stdout + r.stderr)[-12000:]
    summary_line = ""
    for line in reversed(r.stdout.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            summary_line = line.strip()
            break
    return {
        "command": args,
        "exit_code": r.returncode,
        "summary_line": summary_line,
        "started_utc": started,
        "ended_utc": datetime.now(timezone.utc).isoformat(),
        "stdout_tail": tail,
        "quick_subset": quick,
    }


def _version_authority_check() -> dict[str, Any]:
    import yaml

    doc = yaml.safe_load(_VERSION_YAML.read_text(encoding="utf-8")) or {}
    sys_v = str(doc.get("system_version", ""))
    pp = _PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pp, re.M)
    pp_v = m.group(1) if m else ""
    ok = sys_v == "0.5.0" and pp_v == "0.5.0"
    return {
        "pass": ok,
        "VERSION_yaml_system_version": sys_v,
        "pyproject_version": pp_v,
        "note": "Must both be 0.5.0 for seal",
    }


def _module_audit() -> dict[str, Any]:
    docker_product = (_REPO / "Dockerfile.product").read_text(encoding="utf-8")
    docker_ship = (_REPO / "Dockerfile.shipping").read_text(encoding="utf-8")
    bad = re.search(r"COPY\s+research", docker_product + docker_ship, re.I)
    analysis = (_REPO / "runtime" / "services" / "analysis_service.py").read_text(encoding="utf-8")
    has_gate = "project_to_public" in analysis and "core.engine.projection" in analysis
    return {
        "dockerfiles_copy_research": bool(bad),
        "analysis_service_uses_project_to_public": has_gate,
        "pass_exclusion": not bad and has_gate,
    }


def _projection_bypass_scan() -> dict[str, Any]:
    """Product HTTP entrypoints must not import core.pipeline.analyze for primary response."""
    gpt = (_REPO / "runtime" / "api" / "main.py").read_text(encoding="utf-8")
    ship_api = (_REPO / "runtime" / "shipping" / "api_main.py").read_text(encoding="utf-8")
    # Legacy bypass: direct analyze() without projection
    gpt_bypass = bool(
        re.search(r"from\s+runtime\.pipeline\.analyze\s+import\s+analyze", gpt)
        and re.search(r"analyze\s*\(\s*body\.text", gpt)
    )
    ship_bypass = "apply_public_projection" in ship_api or "project_to_public" in ship_api
    # Shipping correctly uses analysis_service only; direct projection in api_main would be suspicious
    ship_ok = "run_structural_analysis" in ship_api and not ship_bypass
    gpt_ok = "run_structural_analysis" in gpt and not gpt_bypass
    return {
        "pass": gpt_ok and ship_ok,
        "gpt_uses_structural_service_not_raw_analyze": gpt_ok,
        "shipping_api_no_direct_projection_import": not ship_bypass,
        "details": "Shipping/API must delegate to analysis_service (projection inside service).",
    }


def _security_audit() -> dict[str, Any]:
    gpt = (_REPO / "runtime" / "api" / "main.py").read_text(encoding="utf-8")
    ship = (_REPO / "runtime" / "shipping" / "api_main.py").read_text(encoding="utf-8")
    return {
        "gpt_api_bearer_gate": "verify_bearer" in gpt,
        "gpt_rate_limit": "_rate_allow" in gpt,
        "shipping_rate_limit": "_rate_limit" in ship,
        "max_input_chars": "HESPERIA_MAX_INPUT_CHARS" in ship or "_MAX_INPUT_CHARS" in ship,
        "shipping_schema_validate": "validate_against_public_schema" in ship,
        "pass": True,
    }


def _endpoint_violations(routes: list[str]) -> list[str]:
    bad: list[str] = []
    for r in routes:
        if r in ALLOWED_SHIPPING_ROUTES:
            continue
        bad.append(r)
    return bad


def _tier1_specs_report() -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    all_ok = True
    for rel in TIER1_SPEC_PATHS:
        p = _REPO / rel
        exists = p.is_file()
        if not exists:
            all_ok = False
        rows.append({"path": rel, "status": "aligned" if exists else "mismatch_missing_spec"})
    return {"all_tier1_present": all_ok, "subsystems": rows}


def _impl_alignment_hints() -> dict[str, Any]:
    """Lightweight implementation presence (not a full spec diff)."""
    checks = [
        ("projection_gate", _REPO / "hesperia" / "engine" / "projection" / "public_projection.py"),
        ("analysis_service", _REPO / "runtime" / "services" / "analysis_service.py"),
        ("schema_guard", _REPO / "runtime" / "shipping" / "schema_guard.py"),
        ("hex_engine", _REPO / "hesperia" / "engine" / "hex_dynamics.py"),
        ("kme", _REPO / "hesperia" / "engine" / "kme"),
        ("extensions_dynamics", _REPO / "hesperia" / "extensions" / "dynamics"),
        ("extensions_triz", _REPO / "hesperia" / "extensions" / "triz"),
    ]
    out = []
    for name, p in checks:
        ok = p.is_file() or (p.is_dir() and any(p.iterdir()))
        out.append({"component": name, "path": str(p.relative_to(_REPO)), "present": bool(ok)})
    return {"implementation_paths": out}


def _calibration_audit() -> dict[str, Any]:
    import yaml

    doc = yaml.safe_load(_VERSION_YAML.read_text(encoding="utf-8")) or {}
    defaults = doc.get("defaults") or {}
    profile = str(defaults.get("calibration_profile", ""))
    reg_refs = [
        "specs/dynamics/HSPR_CALIBRATION_INDEX_v1.md",
        "specs/calibration/calibration_system.md",
        "specs/canon/hspr_calibration_index.md",
    ]
    present = [r for r in reg_refs if (_REPO / r).is_file()]
    return {
        "default_calibration_profile": profile,
        "version_yaml_defaults_ok": bool(profile),
        "registry_spec_paths_found": present,
        "pass": bool(profile) and len(present) >= 1,
        "note": "Magic-number audit is manual; profiles must stay named in VERSION.yaml.",
    }


def _load_extensions_status() -> dict[str, Any]:
    if not _EXTENSION_STATUS.is_file():
        return {"source": None, "extensions": {}}
    import yaml

    raw = yaml.safe_load(_EXTENSION_STATUS.read_text(encoding="utf-8")) or {}
    return {"source": "EXTENSION_STATUS.yaml", "extensions": raw.get("extensions", {})}


def _dependency_lock_fingerprint() -> dict[str, str]:
    parts: list[Path] = [_REPO / "requirements.txt"]
    rt = _REPO / "requirements" / "runtime.txt"
    if rt.is_file():
        parts.append(rt)
    h = hashlib.sha256()
    for p in parts:
        if p.is_file():
            h.update(p.read_bytes())
            h.update(b"\n")
    return {"requirements_fingerprint_sha256": h.hexdigest(), "files": [str(p.relative_to(_REPO)) for p in parts if p.is_file()]}


def _repo_topology_gate(mod_audit: dict[str, Any]) -> bool:
    return bool(
        _VERSION_YAML.is_file()
        and (_REPO / "REPO_STRUCTURE_POLICY.md").is_file()
        and (_REPO / "EXTENSION_STATUS.yaml").is_file()
        and (_REPO / "GENERATED_ARTIFACT_POLICY.md").is_file()
        and not mod_audit.get("dockerfiles_copy_research", True)
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Build release/v0.5.0 sealed audit package")
    ap.add_argument("--quick", action="store_true", help="Shorter pytest subset")
    ap.add_argument(
        "--determinism-only",
        action="store_true",
        help="Only run triplicate determinism and write determinism_report.json (no pytest/full audit)",
    )
    ap.add_argument(
        "--checksums-only",
        action="store_true",
        help="Only recompute checksums.txt for existing release/v0.5.0/ files",
    )
    ap.add_argument(
        "--fixture",
        type=Path,
        default=_FIXTURE_INPUT,
        help="Canonical UTF-8 input file",
    )
    args = ap.parse_args()

    _RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    if args.checksums_only:
        lines: list[str] = []
        for p in sorted(_RELEASE_DIR.iterdir()):
            if p.name == "checksums.txt" or p.is_dir():
                continue
            rel = p.relative_to(_RELEASE_DIR).as_posix()
            lines.append(f"{_sha256_file(p)}  {rel}")
        (_RELEASE_DIR / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"checksums-only: wrote {_RELEASE_DIR / 'checksums.txt'}")
        return 0

    reasons_fail: list[str] = []

    try:
        canonical_text = _read_canonical_input(Path(args.fixture))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    # Snapshot before writing under release/v0.5.0/ (those writes would otherwise look "dirty").
    dirty = _git_dirty()
    if dirty:
        reasons_fail.append("git_worktree_dirty")

    commit = _git_commit()
    now = datetime.now(timezone.utc)
    seal_ts = os.environ.get("HESPERIA_RELEASE_BUILD_TIMESTAMP", "").strip()
    if not seal_ts:
        seal_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    _apply_release_build_env(commit, seal_ts)

    det_ok, primary_hash, hash_list, blobs = _determinism_triplicate(canonical_text)
    byte_identical = blobs[0] == blobs[1] == blobs[2]

    determinism_report: dict[str, Any] = {
        "generated_utc": now.isoformat(),
        "canonical_input_fixture": str(Path(args.fixture).relative_to(_REPO)),
        "input_sha256": _sha256_bytes(canonical_text.encode("utf-8")),
        "input_length_chars": len(canonical_text),
        "command": f"{sys.executable} tools/release/build_release_audit_v0_5_0.py",
        "environment_note": "Set HESPERIA_RELEASE_BUILD_TIMESTAMP + HESPERIA_GIT_COMMIT (via script) for reproducible build_id.",
        "serialization": "json.dumps(..., sort_keys=True, ensure_ascii=False); floats rounded to 10 dp before hash",
        "raw_byte_identical_across_runs": byte_identical,
        "canonical_sha256_run1": hash_list[0],
        "canonical_sha256_run2": hash_list[1],
        "canonical_sha256_run3": hash_list[2],
        "hash_match": det_ok,
        "pass": det_ok,
        "failure_reason": None
        if det_ok
        else f"hash mismatch: {hash_list}",
    }
    if not det_ok:
        reasons_fail.append("determinism_triplicate_failed")
        (_RELEASE_DIR / "determinism_report.json").write_text(
            json.dumps(determinism_report, indent=2) + "\n", encoding="utf-8"
        )
        print("RELEASE SEAL ABORT: determinism failed", file=sys.stderr)
        return 2

    (_RELEASE_DIR / "determinism_report.json").write_text(
        json.dumps(determinism_report, indent=2) + "\n", encoding="utf-8"
    )
    if args.determinism_only:
        print(f"determinism-only: ok sha256={primary_hash}")
        return 0

    # --- SYSTEM SEAL GO/NO-GO (TASK_11): all Tasks 1–10 must be simultaneously satisfied ---
    sys.path.insert(0, str(_REPO))
    from hesperia.system.system_seal import run_system_seal_gate

    seal_report = run_system_seal_gate(_REPO)
    (_RELEASE_DIR / "system_seal.json").write_text(
        json.dumps(seal_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if seal_report.get("status") != "PASS":
        reasons_fail.append("system_seal_gate_failed")
        print("RELEASE SEAL ABORT: system_seal", seal_report.get("status"), file=sys.stderr)
        print(json.dumps(seal_report.get("checks"), indent=2), file=sys.stderr)

    ref_payload = _canonical_analyze_dict(canonical_text)
    ref_path = _RELEASE_DIR / "e2e_reference_output.json"
    ref_path.write_text(
        json.dumps(ref_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not _SCHEMA_SRC.is_file():
        print("Missing", _SCHEMA_SRC, file=sys.stderr)
        return 1
    shutil.copy2(_SCHEMA_SRC, _RELEASE_DIR / "schema.json")
    schema_obj = json.loads(_SCHEMA_SRC.read_text(encoding="utf-8"))

    if _CAPS_SRC.is_file():
        shutil.copy2(_CAPS_SRC, _RELEASE_DIR / "capabilities.yaml")

    specs_index = _build_specs_index()
    (_RELEASE_DIR / "specs_index.json").write_text(
        json.dumps(specs_index, indent=2) + "\n", encoding="utf-8"
    )

    # --- Schema validation (analyze / compare / batch / e2e) ---
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    from runtime.services.analysis_service import run_structural_analysis, run_structural_analysis_batch
    from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile

    assets = _REPO / "assets" / "lexicon" / "curated"
    r1 = run_structural_analysis(canonical_text, assets_root=assets, stages="full")
    r2 = run_structural_analysis(canonical_text + "\u00a0", assets_root=assets, stages="full")
    d1 = (r1.get("L7") or {}) if isinstance(r1, dict) else {}
    d2 = (r2.get("L7") or {}) if isinstance(r2, dict) else {}
    dom1 = (r1.get("usf") or {}).get("raw_metrics") or {} if isinstance(r1, dict) else {}
    dom2 = (r2.get("usf") or {}).get("raw_metrics") or {} if isinstance(r2, dict) else {}

    def _dom_match(m1: dict, m2: dict) -> bool:
        v1 = m1.get("macro_domain_vector") or m1.get("dominant_macro_domain")
        v2 = m2.get("macro_domain_vector") or m2.get("dominant_macro_domain")
        if isinstance(v1, list) and isinstance(v2, list) and v1 and v2:
            i1 = max(range(len(v1)), key=lambda i: v1[i])
            i2 = max(range(len(v2)), key=lambda i: v2[i])
            return i1 == i2
        return False

    def _cd(x: dict, y: dict) -> str:
        c1 = x.get("TRUST_TIER") or x.get("OUTPUT_TRUST_TAG") or ""
        c2 = y.get("TRUST_TIER") or y.get("OUTPUT_TRUST_TAG") or ""
        return "same" if c1 == c2 else "different"

    comparison_core = {
        "run": "compare",
        "text1_preview": canonical_text[:80],
        "text2_preview": (canonical_text + "\u00a0")[:80],
        "result1_trust": d1.get("OUTPUT_TRUST_TAG"),
        "result2_trust": d2.get("OUTPUT_TRUST_TAG"),
        "dominant_match": _dom_match(dom1, dom2),
        "confidence_delta": _cd(d1, d2),
    }
    compare_wrapped = attach_public_output_metadata(
        comparison_core,
        calibration_profile=default_calibration_profile(),
        pipeline_version=api_pipeline_version(),
    )
    batch_rows = run_structural_analysis_batch([canonical_text], assets_root=assets)
    batch_wrapped = attach_public_output_metadata(
        {},
        calibration_profile=default_calibration_profile(),
        pipeline_version=api_pipeline_version(),
    )
    batch_wrapped["payload"] = batch_rows

    schema_results: list[dict[str, Any]] = []
    schema_overall = True
    for label, inst in (
        ("analyze_e2e_reference", ref_payload),
        ("compare_envelope", compare_wrapped),
        ("batch_envelope", batch_wrapped),
    ):
        env_errs = _envelope_minimum_check(inst) if isinstance(inst, dict) else ["not_a_dict"]
        js_errs = _json_schema_validate(inst, schema_obj) if not env_errs else []
        errs = env_errs + js_errs
        ok = not errs
        schema_overall = schema_overall and ok
        schema_results.append({"artifact": label, "pass": ok, "errors": errs[:50]})

    # Public key leak guard on all JSON outputs
    leak_checks: list[dict[str, Any]] = []
    leak_ok = True
    for label, inst in (
        ("e2e_reference", ref_payload),
        ("compare", compare_wrapped),
        ("batch", batch_wrapped),
    ):
        try:
            _leak_scan_public_schema_guard(inst)
            leak_checks.append({"artifact": label, "pass": True, "error": None})
        except ValueError as e:
            leak_ok = False
            leak_checks.append({"artifact": label, "pass": False, "error": str(e)})

    if not schema_overall:
        reasons_fail.append("json_schema_validation_failed")
    if not leak_ok:
        reasons_fail.append("internal_leak_schema_guard_failed")

    schema_validation_report = {
        "generated_utc": now.isoformat(),
        "schema_path_repo_relative": str(_SCHEMA_SRC.relative_to(_REPO)),
        "schema_release_copy": "schema.json",
        "validator": "jsonschema Draft202012Validator + envelope minimum + schema_guard tree walk",
        "results": schema_results,
        "leak_scan_schema_guard": leak_checks,
        "overall_pass": schema_overall and leak_ok,
    }
    (_RELEASE_DIR / "schema_validation_report.json").write_text(
        json.dumps(schema_validation_report, indent=2) + "\n", encoding="utf-8"
    )

    test_report = _run_pytest(args.quick)
    if test_report["exit_code"] != 0:
        reasons_fail.append("pytest_failed")

    ver = _version_authority_check()
    if not ver["pass"]:
        reasons_fail.append("version_authority_mismatch")

    routes = _shipping_routes()
    ev = _endpoint_violations(routes)
    endpoints_ok = not ev
    if not endpoints_ok:
        reasons_fail.append(f"disallowed_shipping_routes:{ev}")

    mod = _module_audit()
    if not mod["pass_exclusion"]:
        reasons_fail.append("module_exclusion_or_projection_gate")

    proj = _projection_bypass_scan()
    if not proj["pass"]:
        reasons_fail.append("projection_bypass_risk")

    tier1 = _tier1_specs_report()
    if not tier1["all_tier1_present"]:
        reasons_fail.append("tier1_spec_missing")

    cal = _calibration_audit()
    if not cal["pass"]:
        reasons_fail.append("calibration_audit")

    sec = _security_audit()
    sec["pass"] = all(
        [
            sec["gpt_api_bearer_gate"],
            sec["gpt_rate_limit"],
            sec["shipping_rate_limit"],
            sec["max_input_chars"],
            sec["shipping_schema_validate"],
        ]
    )
    if not sec["pass"]:
        reasons_fail.append("security_sanity")

    extensions_block = _load_extensions_status()
    dep_fp = _dependency_lock_fingerprint()

    may_tag = not reasons_fail

    audit_report = {
        "generated_utc": now.isoformat(),
        "version_authority": ver,
        "projection_enforcement": {
            "pass": mod["analysis_service_uses_project_to_public"] and proj["pass"],
            "module_audit": mod,
            "bypass_scan": proj,
        },
        "internal_leak_scan": {"pass": leak_ok, "checks": leak_checks},
        "public_endpoint_restrictions": {
            "pass": endpoints_ok,
            "allowed": sorted(ALLOWED_SHIPPING_ROUTES),
            "observed_routes": routes,
            "violations": ev,
        },
        "module_inclusion_exclusion": {
            "pass": mod["pass_exclusion"],
            "dockerfiles_copy_research": mod["dockerfiles_copy_research"],
            "note": "Product Dockerfiles must not COPY research/; analysis_service must use project_to_public.",
        },
        "spec_compliance": {
            "tier1_specs": tier1,
            "implementation_hints": _impl_alignment_hints(),
            "pass": tier1["all_tier1_present"],
        },
        "calibration": cal,
        "security_runtime_sanity": sec,
        "extensions_status": extensions_block,
        "determinism_summary": {
            "pass": det_ok,
            "canonical_sha256": primary_hash,
            "report_file": "determinism_report.json",
        },
        "schema_validation_summary": {
            "pass": schema_overall and leak_ok,
            "report_file": "schema_validation_report.json",
        },
        "pytest": {"pass": test_report["exit_code"] == 0, "report_file": "test_report.json"},
        "system_seal": {
            "pass": seal_report.get("status") == "PASS",
            "status": seal_report.get("status"),
            "checks": seal_report.get("checks"),
            "report_file": "system_seal.json",
        },
        "seal_decision": {
            "may_tag_v0_5_0": may_tag,
            "reasons_fail": reasons_fail,
        },
    }
    (_RELEASE_DIR / "audit_report.json").write_text(
        json.dumps(audit_report, indent=2) + "\n", encoding="utf-8"
    )

    (_RELEASE_DIR / "test_report.json").write_text(
        json.dumps(
            {
                **test_report,
                "spec_compliance_reference": "audit_report.json → spec_compliance.tier1_specs",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cal_profile = cal.get("default_calibration_profile") or "v0_5_0"

    manifest = {
        "system_version": "0.5.0",
        "release_stage": "dynamic_integration",
        "git_commit": commit,
        "build_timestamp": now.isoformat(),
        "envelope_timestamp_utc": seal_ts,
        "git_dirty": dirty,
        "schema_version": "v1",
        "calibration_profile_default": cal_profile,
        "modules": {
            "core": "included",
            "engine": "included",
            "projection": "included",
            "api": "included",
            "cli": "included",
            "schemas": "included",
            "version_system_support": "included",
            "dynamics": "included_internal",
            "triz": "optional",
            "calibration": "internal",
            "clinical": "excluded",
            "research": "excluded",
            "notebooks": "excluded",
            "demos": "excluded",
        },
        "determinism_expected": True,
        "determinism_verified": det_ok,
        "determinism_e2e_sha256": primary_hash,
        "extensions": extensions_block.get("extensions", {}),
        "canonical_statement": (
            "v0.5.0 is the canonical baseline for dynamic HESPERIA (Engine Dynamics sealed multiscale semantic physics)."
        ),
        "shipping_api_routes": routes,
        "audit_artifacts": {
            "audit_report": "audit_report.json",
            "determinism_report": "determinism_report.json",
            "system_seal": "system_seal.json",
            "schema_validation_report": "schema_validation_report.json",
            "test_report": "test_report.json",
            "final_gate_status": "final_gate_status.json",
        },
        "seal_status": "PASS" if may_tag else "FAIL",
        "pytest_quick_subset": args.quick,
    }
    (_RELEASE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    build_info = {
        "system_version": "0.5.0",
        "build_date_utc": now.isoformat(),
        "envelope_timestamp_utc": seal_ts,
        "git_commit": commit,
        "git_dirty": dirty,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "dependency_lock": dep_fp,
        "execution_commands": [
            f"{sys.executable} tools/release/build_release_audit_v0_5_0.py"
            + (" --quick" if args.quick else ""),
            f"canonical_input_fixture={Path(args.fixture).relative_to(_REPO)}",
        ],
        "determinism": determinism_report,
    }
    (_RELEASE_DIR / "build_info.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8")

    repo_topo_ok = _repo_topology_gate(mod)
    final_gate_status: dict[str, Any] = {
        "system_version": "0.5.0",
        "sealed": may_tag,
        "pytest_full_suite_ran": not args.quick,
        "critical_checks": {
            "version_authority": "pass" if ver["pass"] else "fail",
            "repo_topology": "pass" if repo_topo_ok else "fail",
            "spec_consolidation": "pass" if tier1["all_tier1_present"] else "fail",
            "product_boundary": "pass"
            if (
                proj["pass"]
                and endpoints_ok
                and mod["analysis_service_uses_project_to_public"]
                and leak_ok
            )
            else "fail",
            "determinism": "pass" if det_ok else "fail",
            "schema_validation": "pass" if (schema_overall and leak_ok) else "fail",
            "release_audit": "pass"
            if (test_report["exit_code"] == 0 and not args.quick)
            else (
                "fail"
                if test_report["exit_code"] != 0
                else "quick_subset_only"
            ),
            "system_seal": "pass" if seal_report.get("status") == "PASS" else "fail",
        },
        "reasons_fail": reasons_fail,
        "note": (
            "sealed=true matches audit_report.seal_decision.may_tag_v0_5_0; "
            "run without --quick before git tag v0.5.0."
        ),
    }
    (_RELEASE_DIR / "final_gate_status.json").write_text(
        json.dumps(final_gate_status, indent=2) + "\n", encoding="utf-8"
    )

    # Checksums (all files except checksums.txt)
    lines: list[str] = []
    for p in sorted(_RELEASE_DIR.iterdir()):
        if p.name == "checksums.txt" or p.is_dir():
            continue
        rel = p.relative_to(_RELEASE_DIR).as_posix()
        lines.append(f"{_sha256_file(p)}  {rel}")
    (_RELEASE_DIR / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"release audit written: {_RELEASE_DIR}")
    print(f"determinism_e2e_sha256: {primary_hash}")
    print(f"seal_decision may_tag_v0_5_0: {may_tag}")
    if reasons_fail:
        print("FAIL reasons:", "; ".join(reasons_fail), file=sys.stderr)
    if dirty:
        print("WARNING: git working tree dirty — do not tag", file=sys.stderr)

    return 0 if may_tag else 1


if __name__ == "__main__":
    raise SystemExit(main())
