from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd, cwd=str(Path(__file__).resolve().parents[1]))


def test_demo_scripts() -> None:
    _run(["python3", "tools/demo_llm_audit.py", "demo llm text"])
    _run(["python3", "tools/demo_tfp.py", "demo tfp text"])
    _run(["python3", "tools/demo_fingerprint.py", "demo fingerprint text"])

