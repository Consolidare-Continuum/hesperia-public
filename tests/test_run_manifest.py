# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Run manifest tests.
Verify manifest fields, CLI capture, and policy_mode recording.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.provenance.run_manifest import build_run_manifest


class _FakeArgs:
    def __init__(self, text="abc", out=None, profile=None, policy_mode=None, write_dossier=None, validate_dossier=False):
        self.text = text
        self.out = out
        self.profile = profile
        self.policy_mode = policy_mode
        self.write_dossier = write_dossier
        self.validate_dossier = validate_dossier


def test_manifest_fields_present() -> None:
    """build_run_manifest returns policy_mode, profile_id, assets_root, defaults_used, cli_arguments."""
    args = _FakeArgs()
    defaults = {"F": 288, "A": 12}
    manifest = build_run_manifest(args, defaults, None, None, "/path/to/assets")
    assert "policy_mode" in manifest
    assert "profile_id" in manifest
    assert "assets_root" in manifest
    assert "defaults_used" in manifest
    assert "cli_arguments" in manifest


def test_cli_arguments_captured() -> None:
    """cli_arguments contains serialized CLI-like args (text, policy_mode, etc.)."""
    args = _FakeArgs(text="justice and order", policy_mode="STRUCTURE_ONLY", validate_dossier=True)
    manifest = build_run_manifest(args, {}, None, None, None)
    cli = manifest.get("cli_arguments", {})
    assert cli.get("text") == "justice and order"
    assert cli.get("policy_mode") == "STRUCTURE_ONLY"
    assert cli.get("validate_dossier") is True


def test_policy_mode_recorded_correctly() -> None:
    """policy_mode is from args, or defaults, or STRUCTURE_PLUS_CONTEXT."""
    args = _FakeArgs(policy_mode="FULL_INTERPRETATION")
    manifest = build_run_manifest(args, {}, None, None, None)
    assert manifest["policy_mode"] == "FULL_INTERPRETATION"

    args2 = _FakeArgs(policy_mode=None)
    manifest2 = build_run_manifest(args2, {"interpretation_policy_mode": "STRUCTURE_ONLY"}, None, None, None)
    assert manifest2["policy_mode"] == "STRUCTURE_ONLY"

    args3 = _FakeArgs(policy_mode=None)
    manifest3 = build_run_manifest(args3, {}, None, None, None)
    assert manifest3["policy_mode"] == "STRUCTURE_PLUS_CONTEXT"


def test_profile_id_and_assets_root() -> None:
    """profile_id and assets_root are recorded when provided."""
    manifest = build_run_manifest(_FakeArgs(), {}, "my_profile_v1", None, "/repo/lexicon/curated")
    assert manifest["profile_id"] == "my_profile_v1"
    assert manifest["assets_root"] == "/repo/lexicon/curated"


def test_defaults_used_serialized() -> None:
    """defaults_used is a serializable copy of defaults."""
    defaults = {"F": 288, "A": 12, "eps": 1e-9}
    manifest = build_run_manifest(_FakeArgs(), defaults, None, None, None)
    du = manifest["defaults_used"]
    assert du.get("F") == 288
    assert du.get("A") == 12
    assert du.get("eps") == 1e-9


def test_dossier_written_contains_run_manifest() -> None:
    """Written dossier meta contains run_manifest with policy_mode."""
    from runtime.dossier import write_dossier_json
    from runtime.provenance import build_run_manifest, get_engine_provenance

    args = _FakeArgs(policy_mode="STRUCTURE_ONLY")
    manifest = build_run_manifest(args, {"F": 288}, None, None, str(_REPO / "assets" / "lexicon" / "curated"))
    dossier = {"run": "L1_through_L9", "text_preview": "x", "diagnostics": {}}
    for i in range(1, 10):
        dossier[f"L{i}"] = {}
    meta = get_engine_provenance()
    meta["run_manifest"] = manifest
    dossier["meta"] = meta
    path = _REPO / "tests" / "_dossier_manifest.json"
    try:
        write_dossier_json(dossier, path)
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "meta" in data and "run_manifest" in data["meta"]
        rm = data["meta"]["run_manifest"]
        assert rm["policy_mode"] == "STRUCTURE_ONLY"
        assert "cli_arguments" in rm
    finally:
        path.unlink(missing_ok=True)
