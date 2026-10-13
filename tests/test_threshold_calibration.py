from __future__ import annotations

import json
from pathlib import Path
import subprocess


def test_threshold_calibration_report(tmp_path: Path) -> None:
    c = tmp_path / "corpus"
    c.mkdir()
    (c / "a.txt").write_text("short sample", encoding="utf-8")
    (c / "b.txt").write_text("longer sample with more words and narrative flow", encoding="utf-8")
    out = tmp_path / "report.json"
    cmd = [
        "python3",
        "tools/calibrate_product_thresholds.py",
        str(c),
        "--config",
        "assets/config/pipeline.yaml",
        "--out",
        str(out),
    ]
    subprocess.check_call(cmd, cwd=str(Path(__file__).resolve().parents[1]))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "thresholds" in data
    assert "length_bias" in data

