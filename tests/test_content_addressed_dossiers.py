# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Content-addressed dossier tests.
Verify dossier_id derived from checksum, filename when option enabled, index contains dossier_id.
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


def test_dossier_id_derived_from_checksum(tmp_path: Path) -> None:
    """meta.dossier_id is the first 12 characters of dossier_checksum."""
    dossier = {
        "run": "L1_through_L9",
        "text_preview": "test",
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
    out = tmp_path / "d.json"
    dossier_id = write_dossier_json(dossier, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    checksum = data.get("dossier_checksum") or data.get("meta", {}).get("dossier_checksum")
    assert checksum
    assert dossier_id == checksum[:12]
    assert data.get("meta", {}).get("dossier_id") == dossier_id


def test_filename_matches_id_when_option_enabled(tmp_path: Path) -> None:
    """With --content-addressed, dossiers are written as dossier_<id>.json."""
    (tmp_path / "a.txt").write_text("one")
    (tmp_path / "b.txt").write_text("two")
    out_dir = tmp_path / "out"
    run_batch(
        [tmp_path / "a.txt", tmp_path / "b.txt"],
        out_dir,
        content_addressed=True,
        index_path=tmp_path / "index.json",
    )
    files = sorted(out_dir.glob("dossier_*.json"))
    assert len(files) == 2
    for p in files:
        assert p.stem.startswith("dossier_")
        suffix = p.stem.replace("dossier_", "")
        assert len(suffix) == 12
        assert all(c in "0123456789abcdef" for c in suffix)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data.get("meta", {}).get("dossier_id") == suffix


def test_index_contains_dossier_id(tmp_path: Path) -> None:
    """Index entries include dossier_id after writing dossiers."""
    (tmp_path / "x.txt").write_text("content")
    out_dir = tmp_path / "results"
    index_path = tmp_path / "idx.json"
    run_batch(
        [tmp_path / "x.txt"],
        out_dir,
        index_path=index_path,
    )
    data = _load_index(Path(index_path))
    assert len(data["dossiers"]) == 1
    entry = data["dossiers"][0]
    assert "dossier_id" in entry
    assert len(entry["dossier_id"]) == 12
    dossier_path = out_dir / "dossier_001.json"
    dossier_data = json.loads(dossier_path.read_text(encoding="utf-8"))
    assert dossier_data.get("meta", {}).get("dossier_id") == entry["dossier_id"]
