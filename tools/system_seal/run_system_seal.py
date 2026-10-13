#!/usr/bin/env python3
# HESPERIA — System seal GO/NO-GO gate (TASK_11).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root on PYTHONPATH or cwd):
#   python3 -m tools.system_seal.run_system_seal
#
# Exit 0 iff status == PASS.

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo))
    from hesperia.system.system_seal import run_system_seal_gate

    report = run_system_seal_gate(repo)
    ver_doc = yaml.safe_load((repo / "VERSION.yaml").read_text(encoding="utf-8")) or {}
    sys_ver = str(ver_doc.get("system_version", "0.5.1"))
    out_path = repo / "release" / f"v{sys_ver}" / "system_seal.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
