from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_validate_dict_a_cli_ok(tmp_path: Path) -> None:
    sample = tmp_path / "dict_a_sample.jsonl"
    sample.write_text(
        json.dumps(
            {
                "entry_id": "A-1",
                "surface_form": "identity diffusion",
                "normalized_form": "identity diffusion",
                "match_type": "phrase",
                "candidate_concept_ids": ["C-1"],
                "priority": 10,
                "version": "v0.6.0"
            }
        )
        + "\n",
        encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dict_a.py"), str(sample)],
        capture_output=True,
        text=True,
        check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_dict_a_cli_default_paths_ok() -> None:
    """No-args mode validates pinned pack under assets (consolidation / CI parity)."""
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dict_a.py")],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_dict_b_dlcr_cli_default_paths_ok() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dict_b_dlcr.py")],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_dict_b_dlcr_cli_ok(tmp_path: Path) -> None:
    sample = tmp_path / "dict_b_sample.jsonl"
    sample.write_text(
        json.dumps(
            {
                "concept_id": "C-1",
                "preferred_label": "identity diffusion",
                "definition": "instability in self-definition",
                "family_ids": ["F1"],
                "area_ids": ["A1"],
                "specificity_rank": 2,
                "status": "active",
                "version": "v0.6.0"
            }
        )
        + "\n",
        encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "validate_dict_b_dlcr.py"), str(sample)],
        capture_output=True,
        text=True,
        check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr

