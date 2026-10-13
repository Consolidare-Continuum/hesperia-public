# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Parallel batch runner tests.
Verify results equal to sequential, index entries correct, no duplicate entries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.pipeline.batch_runner import run_batch


def test_parallel_results_equal_to_sequential(tmp_path: Path) -> None:
    """Running with workers=1 and workers=2 produces identical analysis results per text (L1–L9, policy)."""
    texts = ["justice and order", "freedom and truth", "fairness and harm"]
    for i, t in enumerate(texts, start=1):
        (tmp_path / f"f{i}.txt").write_text(t)
    input_files = [tmp_path / "f1.txt", tmp_path / "f2.txt", tmp_path / "f3.txt"]
    index_seq = tmp_path / "index_seq.json"
    index_par = tmp_path / "index_par.json"
    out_seq = tmp_path / "out_seq"
    out_par = tmp_path / "out_par"

    run_batch(input_files, out_seq, policy_mode="STRUCTURE_PLUS_CONTEXT", index_path=index_seq, workers=1)
    run_batch(input_files, out_par, policy_mode="STRUCTURE_PLUS_CONTEXT", index_path=index_par, workers=2)

    for i in range(1, 4):
        p1 = out_seq / f"dossier_{i:03d}.json"
        p2 = out_par / f"dossier_{i:03d}.json"
        assert p1.exists() and p2.exists()
        d1 = json.loads(p1.read_text(encoding="utf-8"))
        d2 = json.loads(p2.read_text(encoding="utf-8"))
        assert d1.get("text_preview") == d2.get("text_preview")
        assert (d1.get("meta") or {}).get("run_manifest", {}).get("policy_mode") == (
            (d2.get("meta") or {}).get("run_manifest", {}).get("policy_mode")
        )
        for layer in ("L1", "L7", "L9"):
            assert layer in d1 and layer in d2
            assert d1[layer] == d2[layer], f"{layer} differs for dossier_{i:03d}"


def test_parallel_index_entries_correct(tmp_path: Path) -> None:
    """After parallel run, index has one entry per written dossier."""
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "b.txt").write_text("beta")
    (tmp_path / "c.txt").write_text("gamma")
    out_dir = tmp_path / "results"
    index_path = tmp_path / "index.json"
    written = run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"],
        out_dir,
        workers=3,
        index_path=index_path,
    )
    assert len(written) == 3
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    entries = index_data.get("dossiers", [])
    assert len(entries) == 3
    paths_in_index = {e["path"] for e in entries}
    for p in written:
        assert str(p.resolve()) in paths_in_index


def test_parallel_no_duplicate_entries(tmp_path: Path) -> None:
    """Parallel run does not add duplicate checksums or paths to the index."""
    (tmp_path / "x.txt").write_text("one")
    (tmp_path / "y.txt").write_text("two")
    out_dir = tmp_path / "out"
    index_path = tmp_path / "idx.json"
    run_batch(
        [tmp_path / "x.txt", tmp_path / "y.txt"],
        out_dir,
        workers=2,
        index_path=index_path,
    )
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    entries = index_data.get("dossiers", [])
    checksums = [e.get("checksum") for e in entries]
    paths = [e.get("path") for e in entries]
    assert len(checksums) == len(set(checksums)), "duplicate checksums in index"
    assert len(paths) == len(set(paths)), "duplicate paths in index"
