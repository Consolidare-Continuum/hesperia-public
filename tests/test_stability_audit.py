from __future__ import annotations

import json
from pathlib import Path
import subprocess


def test_stability_audit_report(tmp_path: Path) -> None:
    inp = tmp_path / "in.txt"
    inp.write_text("stability audit sample", encoding="utf-8")
    out = tmp_path / "audit.json"
    cmd = [
        "python3",
        "tools/stability_audit.py",
        str(inp),
        "--config",
        "assets/config/pipeline.yaml",
        "--runs",
        "3",
        "--out",
        str(out),
    ]
    subprocess.check_call(cmd, cwd=str(Path(__file__).resolve().parents[1]))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["runs"] == 3
    assert "project_hash_identical" in data

