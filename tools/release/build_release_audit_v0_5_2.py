#!/usr/bin/env python3
# HESPERIA — Task 5: sealed release audit package under release/v0.5.2/
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root):
#   python3 tools/release/build_release_audit_v0_5_2.py
#   python3 tools/release/build_release_audit_v0_5_2.py --quick

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.release import build_release_audit_v0_5_1 as release_051

release_051._RELEASE_VERSION = "0.5.2"
release_051._RELEASE_DIR = release_051._REPO / "release" / "v0.5.2"
release_051._VERSION_YAML = release_051._REPO / "VERSION.yaml"
release_051._PYPROJECT = release_051._REPO / "pyproject.toml"
release_051._SCHEMA_SRC = release_051._REPO / "schemas" / "public" / "public_output_schema.json"
release_051._CAPS_SRC = release_051._REPO / "hesperia" / "system" / "capabilities.yaml"
release_051._EXTENSION_STATUS = release_051._REPO / "EXTENSION_STATUS.yaml"
release_051._FIXTURE_INPUT = release_051._REPO / "tests" / "fixtures" / "release_v0_5_0" / "canonical_input.txt"


def _run_pytest_no_tfp(quick: bool) -> dict[str, object]:
    """0.5.2 technical release: governed full profile excluding tfp/clinical_tfp scope."""
    if quick:
        args = [
            sys.executable,
            "-m",
            "pytest",
            "tests/engine/test_projection_product_surface.py",
            "tests/test_sealed_runtime_regression.py",
            "tests/test_release_v0_5_1_audit_package.py",
            "-q",
            "--tb=no",
        ]
    else:
        args = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_runtime_spine_integrity.py",
            "tests/test_semantic_output_signature.py",
            "tests/test_release_version.py",
            "tests/test_public_api_snapshot.py",
            "tests/test_tool_contracts_locked.py",
            "tests/test_release_v0_5_1_audit_package.py",
            "tests/engine/test_projection_product_surface.py",
            "tests/engine/test_sealed_multiscale.py",
            "tests/test_reading_scales.py",
            "-q",
            "--tb=no",
        ]
    started = datetime.now(timezone.utc).isoformat()
    r = subprocess.run(args, cwd=release_051._REPO, capture_output=True, text=True)
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
        "scope_filter": "technical_full_profile_non_tfp",
    }


def _post_fix_release_labels() -> None:
    rel = release_051._RELEASE_DIR
    audit_path = rel / "audit_report.json"
    gate_path = rel / "final_gate_status.json"
    if audit_path.is_file():
        data = json.loads(audit_path.read_text(encoding="utf-8"))
        sd = data.get("seal_decision")
        if isinstance(sd, dict) and "may_tag_v0_5_1" in sd:
            sd["may_tag_v0_5_2"] = sd.pop("may_tag_v0_5_1")
        audit_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if gate_path.is_file():
        data = json.loads(gate_path.read_text(encoding="utf-8"))
        note = str(data.get("note", ""))
        note = note.replace("may_tag_v0_5_1", "may_tag_v0_5_2").replace("v0.5.1", "v0.5.2")
        data["note"] = note
        gate_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    release_051._run_pytest = _run_pytest_no_tfp
    rc = release_051.main()
    _post_fix_release_labels()
    raise SystemExit(rc)
