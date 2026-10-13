# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Batch runner tests.
Verify multiple files processed, dossiers written, index updated, policy mode applied.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.pipeline.batch_runner import resolve_inputs, run_batch


def test_multiple_files_processed(tmp_path: Path) -> None:
    """Batch processes multiple text files and returns one dossier path per file."""
    (tmp_path / "a.txt").write_text("justice and order")
    (tmp_path / "b.txt").write_text("freedom and truth")
    (tmp_path / "c.txt").write_text("fairness and harm")
    out_dir = tmp_path / "batch_results"
    index_path = tmp_path / "index.json"
    written = run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"],
        out_dir,
        policy_mode="STRUCTURE_PLUS_CONTEXT",
        index_path=index_path,
    )
    assert len(written) == 3
    assert written[0].name == "dossier_001.json"
    assert written[1].name == "dossier_002.json"
    assert written[2].name == "dossier_003.json"


def test_dossiers_written(tmp_path: Path) -> None:
    """Written dossiers exist and contain run + meta with run_manifest."""
    (tmp_path / "one.txt").write_text("one text")
    (tmp_path / "two.txt").write_text("two text")
    out_dir = tmp_path / "out"
    written = run_batch(
        [tmp_path / "one.txt", tmp_path / "two.txt"],
        out_dir,
        policy_mode="FULL_INTERPRETATION",
        index_path=tmp_path / "idx.json",
    )
    assert len(written) == 2
    for p in written:
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "run" in data
        assert "meta" in data
        assert "run_manifest" in data["meta"]
        assert data["meta"]["run_manifest"]["policy_mode"] == "FULL_INTERPRETATION"


def test_index_updated(tmp_path: Path) -> None:
    """After run_batch, the dossier index contains entries for each written dossier."""
    (tmp_path / "x.txt").write_text("first")
    (tmp_path / "y.txt").write_text("second")
    out_dir = tmp_path / "results"
    index_path = tmp_path / "dossier_index.json"
    written = run_batch(
        [tmp_path / "x.txt", tmp_path / "y.txt"],
        out_dir,
        index_path=index_path,
    )
    assert index_path.exists()
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    dossiers = index_data.get("dossiers", [])
    assert len(dossiers) == 2
    paths_in_index = {e["path"] for e in dossiers}
    for p in written:
        assert str(p.resolve()) in paths_in_index


def test_policy_mode_applied_consistently(tmp_path: Path) -> None:
    """All dossiers in a batch have the requested policy_mode in run_manifest."""
    (tmp_path / "p1.txt").write_text("alpha")
    (tmp_path / "p2.txt").write_text("beta")
    out_dir = tmp_path / "policy_out"
    run_batch(
        [tmp_path / "p1.txt", tmp_path / "p2.txt"],
        out_dir,
        policy_mode="STRUCTURE_ONLY",
        index_path=tmp_path / "idx.json",
    )
    for p in sorted(out_dir.glob("dossier_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["meta"]["run_manifest"]["policy_mode"] == "STRUCTURE_ONLY"


def test_resolve_inputs_directory(tmp_path: Path) -> None:
    """Single directory path resolves to .txt files."""
    (tmp_path / "f1.txt").write_text("a")
    (tmp_path / "f2.txt").write_text("b")
    entries = resolve_inputs([tmp_path])
    assert len(entries) == 2
    labels = sorted(e[0] for e in entries)
    assert labels == ["f1", "f2"]


def test_resolve_inputs_json_list(tmp_path: Path) -> None:
    """Single .json path with array of strings resolves to list of (item_XXX, text)."""
    (tmp_path / "list.json").write_text('["hello", "world"]')
    entries = resolve_inputs([tmp_path / "list.json"])
    assert len(entries) == 2
    assert entries[0][0] == "item_000" and entries[0][1] == "hello"
    assert entries[1][0] == "item_001" and entries[1][1] == "world"
