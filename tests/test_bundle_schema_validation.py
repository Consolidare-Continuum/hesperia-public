# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.engine.output_anomalies import aggregate_file_envelope, default_operational_envelope

_REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not _REPO.is_dir(), reason="repo root")
def test_validate_tfp_bundle_schemas_minimal_01(tmp_path: Path) -> None:
    row_env = default_operational_envelope()
    body = {
        "run": "tfp_file_pipeline_structural",
        "session_count": 1,
        "structural_batch": [{"session_id": "x", "operational_envelope": row_env}],
        "operational_envelope": aggregate_file_envelope([row_env]),
    }
    d = tmp_path / "bundle"
    d.mkdir()
    (d / "01_structural_batch.json").write_text(json.dumps(body), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_REPO / "tools" / "validate_tfp_bundle_schemas.py"), "--bundle-dir", str(d)],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
