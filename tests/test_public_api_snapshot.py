"""Public output JSON Schema snapshot must match canonical (drift gate)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_public_api_snapshot_matches_canonical() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "tools" / "verify_public_api_snapshot.py"
    r = subprocess.run([sys.executable, str(script), "--repo", str(root)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
