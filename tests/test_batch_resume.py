# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Batch resume tests.
Verify existing dossiers skipped, missing processed, index remains correct.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.dossier import write_dossier_json, verify_dossier_checksum
from runtime.dossier.index_manager import _load_index, update_dossier_index
from runtime.pipeline.batch_runner import run_batch


def _minimal_dossier() -> dict:
    return {
        "run": "L1_through_L9",
        "text_preview": "preview",
        "L1": {},
        "L2": {},
        "L3": {},
        "L4": {},
        "L5": {},
        "L6": {},
        "L7": {},
        "L8": {},
        "L9": {},
        "diagnostics": {},
    }


def test_existing_dossiers_skipped(tmp_path: Path) -> None:
    """With --resume, existing valid dossiers are skipped (no re-run)."""
    (tmp_path / "a.txt").write_text("first")
    (tmp_path / "b.txt").write_text("second")
    (tmp_path / "c.txt").write_text("third")
    out_dir = tmp_path / "out"
    index_path = tmp_path / "index.json"
    # First run: create dossiers 001 and 002 only (simulate partial run)
    run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt"],
        out_dir,
        index_path=index_path,
        resume=False,
    )
    assert (out_dir / "dossier_001.json").exists()
    assert (out_dir / "dossier_002.json").exists()
    # Pre-create a valid dossier_003 so we have 3 inputs but 003 already exists
    run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"],
        out_dir,
        index_path=index_path,
        resume=False,
    )
    # Now run with resume and same 3 inputs: should skip all 3 (all exist and valid)
    import io
    err = io.StringIO()
    written = run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"],
        out_dir,
        index_path=index_path,
        resume=True,
    )
    # With resume, we skip existing valid; we should have written 0 new ones
    assert len(written) == 0
    assert (out_dir / "dossier_003.json").exists()


def test_missing_dossiers_processed(tmp_path: Path) -> None:
    """With --resume, only missing dossiers are processed."""
    for i, text in enumerate(["one", "two", "three", "four"], start=1):
        (tmp_path / f"f{i}.txt").write_text(text)
    out_dir = tmp_path / "results"
    index_path = tmp_path / "idx.json"
    inputs = [tmp_path / "f1.txt", tmp_path / "f2.txt", tmp_path / "f3.txt", tmp_path / "f4.txt"]
    # Write only dossier_001 and dossier_002 manually (valid dossiers)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in (1, 2):
        d = _minimal_dossier()
        write_dossier_json(d, out_dir / f"dossier_{i:03d}.json")
    # Verify they are valid (checksum was added by write_dossier_json)
    assert verify_dossier_checksum(out_dir / "dossier_001.json")
    assert verify_dossier_checksum(out_dir / "dossier_002.json")
    # Run with resume: should skip 001, 002 and run 003, 004
    written = run_batch(inputs, out_dir, index_path=index_path, resume=True)
    assert len(written) == 2
    assert (out_dir / "dossier_003.json").exists()
    assert (out_dir / "dossier_004.json").exists()
    # Written paths should be 003 and 004
    names = {p.name for p in written}
    assert names == {"dossier_003.json", "dossier_004.json"}


def test_index_remains_correct(tmp_path: Path) -> None:
    """When resuming, skipped dossiers are added to index if missing; index stays consistent."""
    (tmp_path / "x.txt").write_text("x")
    (tmp_path / "y.txt").write_text("y")
    out_dir = tmp_path / "out"
    index_path = tmp_path / "index.json"
    # Run once without resume to create both dossiers and index
    run_batch(
        [tmp_path / "x.txt", tmp_path / "y.txt"],
        out_dir,
        index_path=index_path,
        resume=False,
    )
    data_before = _load_index(Path(index_path))
    count_before = len(data_before["dossiers"])
    assert count_before == 2
    # Run again with resume: skip both, but ensure they're in index (update_dossier_index is idempotent by checksum)
    written = run_batch(
        [tmp_path / "x.txt", tmp_path / "y.txt"],
        out_dir,
        index_path=index_path,
        resume=True,
    )
    assert len(written) == 0
    data_after = _load_index(Path(index_path))
    assert len(data_after["dossiers"]) == 2
    paths = {e["path"] for e in data_after["dossiers"]}
    assert str((out_dir / "dossier_001.json").resolve()) in paths
    assert str((out_dir / "dossier_002.json").resolve()) in paths
