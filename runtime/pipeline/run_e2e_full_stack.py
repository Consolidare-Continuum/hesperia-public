#!/usr/bin/env python3
# HESPERIA — Single encompassing E2E: all run_e2e_all artifacts + product surface + physics + system seal + manifest.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
#
# Usage:
#   python3 -m runtime.pipeline.run_e2e_full_stack [--out-dir DIR] [--text "..."] [--calibration-batch-n N]
#       [--no-dynamics] [--skip-physics] [--skip-seal]
#
# Default: enables Ethan/field-dynamics env (same intent as tools/e2e_full_deliverables.sh), runs physics validation
# once, then system seal with skip_physics_subprocess=True to avoid duplicate pytest.

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_TEXT = (
    "Patient reports severe anxiety when considering work deadlines but also feels guilty resting. "
    "The team demands faster delivery while quality must not slip. Internal conflict between autonomy and compliance."
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _apply_dynamics_env() -> None:
    """Match tools/e2e_full_deliverables.sh — full dynamics + multiscale capability matrix."""
    os.environ["HESPERIA_FIELD_DYNAMICS"] = "1"
    os.environ["HESPERIA_FIELD_DYNAMICS_PHASE2"] = "1"
    os.environ["HESPERIA_FIELD_DYNAMICS_PHASE3"] = "1"
    os.environ["HESPERIA_FIELD_DYNAMICS_PHASE4"] = "1"
    os.environ["HESPERIA_FIELD_DYNAMICS_TRIZ"] = "1"
    os.environ["HESPERIA_FIELD_DYNAMICS_XI"] = "1"
    os.environ["HESPERIA_E2E_MULTISCALE"] = "1"


def _run_physics_validation(repo: Path) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "tests.physics_validation.run_all"]
    r = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=900)
    tail = (r.stdout + r.stderr)[-4000:] if r.returncode != 0 else ""
    return r.returncode, tail


def _write_product_surface(out_dir: Path, text: str) -> Path:
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.shipping.schema_guard import validate_against_public_schema

    assets = _REPO / "assets" / "lexicon" / "curated"
    summary_payload = run_structural_analysis(text, assets_root=assets, stages="full")
    validate_against_public_schema(summary_payload)
    path = out_dir / "run_output_e2e_full_product_surface.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def run_e2e_full_stack(
    out_dir: Path | None = None,
    text: str | None = None,
    *,
    calibration_batch_n: int | None = None,
    dynamics: bool = True,
    run_physics: bool = True,
    run_seal: bool = True,
) -> dict[str, Any]:
    """
    Execute the full stack and write ``run_output_e2e_full_stack_manifest.json`` under ``out_dir``.

    When ``run_physics`` and ``run_seal`` are both True, physics runs first and the system seal uses
    ``skip_physics_subprocess=True`` so pytest is not invoked twice.

    Returns the manifest dict (also written to disk).
    """
    from hesperia.system.version import attach_public_output_metadata, default_calibration_profile, e2e_pipeline_version
    from runtime.pipeline.run_e2e_all import run_all

    repo = _REPO
    out = Path(out_dir) if out_dir is not None else repo / "assets" / "artifacts" / "e2e_full_stack"
    out.mkdir(parents=True, exist_ok=True)
    text_in = (text or _DEFAULT_TEXT).strip()

    if calibration_batch_n is not None:
        os.environ["HESPERIA_E2E_CALIBRATION_BATCH_N"] = str(max(1, min(int(calibration_batch_n), 500)))

    if dynamics:
        _apply_dynamics_env()

    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    physics_rc: int | None = None
    physics_tail = ""
    seal_report: dict[str, Any] | None = None
    skip_physics_in_seal = False

    # 1) All standard E2E artifacts (+ optional field_dynamics)
    t0 = datetime.now(timezone.utc).isoformat()
    try:
        written = run_all(out_dir=out, text=text_in)
        steps.append({"step": "run_e2e_all", "ok": True, "outputs": len(written)})
    except Exception as e:
        steps.append({"step": "run_e2e_all", "ok": False, "error": str(e)})
        errors.append(f"run_e2e_all: {e}")
        written = {}

    # 2) Product surface (same text, schema-guarded, under unified out dir)
    try:
        prod_path = _write_product_surface(out, text_in)
        written["run_output_e2e_full_product_surface.json"] = prod_path
        try:
            prod_rel = str(prod_path.resolve().relative_to(repo.resolve())).replace("\\", "/")
        except ValueError:
            prod_rel = str(prod_path.resolve())
        steps.append({"step": "product_surface", "ok": True, "path": prod_rel})
    except Exception as e:
        steps.append({"step": "product_surface", "ok": False, "error": str(e)})
        errors.append(f"product_surface: {e}")

    # 3) Physics validation (standalone, so seal can skip duplicate)
    if run_physics:
        physics_rc, physics_tail = _run_physics_validation(repo)
        ok_ph = physics_rc == 0
        steps.append(
            {
                "step": "physics_validation",
                "ok": ok_ph,
                "exit_code": physics_rc,
                "tail": physics_tail if not ok_ph else "",
            }
        )
        if not ok_ph:
            errors.append(f"physics_validation exit {physics_rc}")
        # Avoid duplicate pytest when physics already passed; seal still runs other checks.
        skip_physics_in_seal = bool(run_physics and physics_rc == 0)

    # 4) System seal GO/NO-GO
    if run_seal:
        from hesperia.system.system_seal import run_system_seal_gate

        try:
            seal_report = run_system_seal_gate(repo, skip_physics_subprocess=skip_physics_in_seal)
            ok_seal = seal_report.get("status") == "PASS"
            steps.append({"step": "system_seal", "ok": ok_seal, "status": seal_report.get("status")})
            if not ok_seal:
                errors.append("system_seal: FAIL")
        except Exception as e:
            seal_report = {"status": "FAIL", "error": str(e)}
            steps.append({"step": "system_seal", "ok": False, "error": str(e)})
            errors.append(f"system_seal: {e}")

    # 5) Artifact index (repo-relative paths when under repo, else absolute)
    artifact_entries: list[dict[str, Any]] = []
    repo_res = repo.resolve()
    for name, p in sorted(written.items(), key=lambda x: x[0]):
        if not isinstance(p, Path) or not p.is_file():
            continue
        pres = p.resolve()
        try:
            rel_s = str(pres.relative_to(repo_res)).replace("\\", "/")
        except ValueError:
            rel_s = str(pres)
        st = p.stat()
        artifact_entries.append(
            {
                "basename": name,
                "path": rel_s,
                "bytes": st.st_size,
                "sha256": _sha256_file(p),
            }
        )

    try:
        out_dir_s = str(out.resolve().relative_to(repo_res)).replace("\\", "/")
    except ValueError:
        out_dir_s = str(out.resolve())

    manifest_body: dict[str, Any] = {
        "run": "e2e_full_stack",
        "started_utc": t0,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "input_text_preview": text_in[:240] + ("…" if len(text_in) > 240 else ""),
        "out_dir": out_dir_s,
        "dynamics_env": bool(dynamics),
        "calibration_batch_n": int(os.environ.get("HESPERIA_E2E_CALIBRATION_BATCH_N", "100")),
        "steps": steps,
        "physics_validation_exit_code": physics_rc,
        "system_seal_skip_physics_subprocess": skip_physics_in_seal,
        "system_seal": seal_report,
        "artifacts": artifact_entries,
        "artifact_count": len(artifact_entries),
        "errors": errors,
        "ok": len(errors) == 0,
    }

    manifest = attach_public_output_metadata(
        manifest_body,
        calibration_profile=default_calibration_profile(),
        pipeline_version=e2e_pipeline_version(),
        execution_flow_version=e2e_pipeline_version(),
        orchestration_mode="E2E_FULL_STACK",
        modules_used=[
            "runtime.pipeline.run_e2e_all",
            "runtime.pipeline.run_e2e_full_stack",
            "runtime.services.analysis_service",
            "tests.physics_validation",
            "hesperia.system.system_seal",
        ],
    )

    mpath = out / "run_output_e2e_full_stack_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    try:
        manifest["manifest_path"] = str(mpath.resolve().relative_to(repo_res)).replace("\\", "/")
    except ValueError:
        manifest["manifest_path"] = str(mpath.resolve())
    return manifest


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Full encompassing E2E: run_e2e_all + product JSON + physics_validation + system_seal + manifest.",
    )
    ap.add_argument("--out-dir", type=Path, default=None, help="Output directory (default: assets/artifacts/e2e_full_stack)")
    ap.add_argument("--text", default=None, help="Shared input text for structural / product flows")
    ap.add_argument(
        "--calibration-batch-n",
        type=int,
        default=None,
        metavar="N",
        help="Override HESPERIA_E2E_CALIBRATION_BATCH_N for calibration structural+summary",
    )
    ap.add_argument("--no-dynamics", action="store_true", help="Do not set HESPERIA_FIELD_DYNAMICS* / multiscale env")
    ap.add_argument("--skip-physics", action="store_true", help="Skip tests.physics_validation (seal will run it if --skip-seal not set)")
    ap.add_argument("--skip-seal", action="store_true", help="Skip hesperia.system.system_seal gate")

    args = ap.parse_args()
    out_dir = args.out_dir or (_REPO / "assets" / "artifacts" / "e2e_full_stack")

    try:
        manifest = run_e2e_full_stack(
            out_dir=out_dir,
            text=args.text,
            calibration_batch_n=args.calibration_batch_n,
            dynamics=not args.no_dynamics,
            run_physics=not args.skip_physics,
            run_seal=not args.skip_seal,
        )
    except Exception as e:
        print(f"e2e_full_stack failed: {e}", file=sys.stderr)
        return 1

    mpath = out_dir / "run_output_e2e_full_stack_manifest.json"
    print(mpath.resolve(), file=sys.stderr)
    print(
        f"e2e_full_stack_ok ok={manifest.get('ok')} artifacts={manifest.get('artifact_count')} "
        f"seal={manifest.get('system_seal', {}).get('status')!r}",
        file=sys.stderr,
    )
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
