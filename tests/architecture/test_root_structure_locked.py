# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
RAD guard: root is a closed set (REPO_STRUCTURE_POLICY.md, repo_refresh_manifest.yaml).

A new top-level directory appearing at repo root without repo_refresh_manifest.yaml and
REPO_STRUCTURE_POLICY.md being updated in the same change is a bug, not a feature — see
REPO_STRUCTURE_POLICY.md "Adding a 16th directory" for the actual process.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Anything here is not part of the 15+1 count: VCS/tooling/venv/cache state, not repo structure.
_IGNORED = frozenset(
    {
        ".git", ".github", ".venv", ".venv.bak-alunel-py313-20260614",
        ".pytest_cache", "__pycache__", "dist",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _manifest() -> dict:
    text = (_repo_root() / "repo_refresh_manifest.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def test_root_directory_set_matches_manifest():
    """Every real top-level directory must be exactly active_paths + research_paths + generated_paths."""
    repo = _repo_root()
    m = _manifest()
    expected_dirs = set(m.get("active_paths") or []) | set(m.get("research_paths") or []) | set(
        m.get("generated_paths") or []
    )
    expected_symlinks = set(m.get("symlink_paths") or [])

    actual_dirs = set()
    actual_symlinks = set()
    for entry in repo.iterdir():
        name = entry.name
        if name.startswith(".") or name in _IGNORED:
            continue
        if entry.is_symlink():
            actual_symlinks.add(name)
        elif entry.is_dir():
            actual_dirs.add(name)

    extra = actual_dirs - expected_dirs
    missing = expected_dirs - actual_dirs
    assert not extra, (
        f"Undocumented root director{'y' if len(extra) == 1 else 'ies'} {sorted(extra)} — "
        "add to repo_refresh_manifest.yaml + REPO_STRUCTURE_POLICY.md, or move it under "
        "assets/, tools/, or docs/ instead. See REPO_STRUCTURE_POLICY.md 'Adding a 16th directory'."
    )
    assert not missing, (
        f"repo_refresh_manifest.yaml lists {sorted(missing)} but no such root directory exists — "
        "manifest is stale, update it to match reality."
    )
    assert actual_symlinks == expected_symlinks, (
        f"root symlinks {sorted(actual_symlinks)} != manifest symlink_paths {sorted(expected_symlinks)}"
    )


def test_policy_doc_exists_and_is_referenced():
    """REPO_STRUCTURE_POLICY.md must exist — the manifest's header claims it as a companion doc."""
    policy = _repo_root() / "REPO_STRUCTURE_POLICY.md"
    assert policy.is_file(), "REPO_STRUCTURE_POLICY.md missing — repo_refresh_manifest.yaml's header cites it"
    text = policy.read_text(encoding="utf-8")
    manifest_names = set((_manifest().get("active_paths") or [])) | set(
        (_manifest().get("research_paths") or [])
    )
    undocumented = {name for name in manifest_names if name not in text}
    assert not undocumented, f"REPO_STRUCTURE_POLICY.md doesn't mention: {sorted(undocumented)}"
