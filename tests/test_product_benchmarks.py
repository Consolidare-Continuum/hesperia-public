from __future__ import annotations

import json
from pathlib import Path
import subprocess


def test_product_benchmark_report(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    subprocess.check_call(
        ["python3", "tools/product_benchmark_eval.py", "--out", str(out)],
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"llm_audit", "tfp_analysis", "document_fingerprint"}

