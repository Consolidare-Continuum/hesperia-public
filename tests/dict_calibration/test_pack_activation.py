# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W9 — atomic pack activation, startup validation, rollback tests.

Reuses the real ``release_case`` fixture from test_freeze_core_candidate.py
so activation is tested against a genuinely valid, freeze-produced v2
candidate bundle — not a hand-faked manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.dict_calibration.test_freeze_core_candidate import release_case  # noqa: F401
from tools.dict_calibration import pack_activation, release_freeze


def _second_bundle(release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Produce a second, genuinely distinct valid candidate bundle by
    perturbing the ledger's random_seed (a real generation-identity field)."""
    ledger = json.loads(release_case["ledger"].read_text(encoding="utf-8"))
    identity_payload = {k: v for k, v in ledger.items() if k not in ("generation_id", "generation_started_at")}
    identity_payload["random_seed"] = 99
    new_ledger = {
        **{k: v for k, v in ledger.items() if k != "generation_id"},
        "random_seed": 99,
        "generation_id": hashlib.sha256(
            release_freeze.canonical_bytes(identity_payload)
        ).hexdigest(),
    }
    ledger_path = tmp_path / "generation_ledger_2.json"
    ledger_path.write_bytes(release_freeze.canonical_bytes(new_ledger))
    ledger_sha256 = hashlib.sha256(ledger_path.read_bytes()).hexdigest()

    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    destination_2 = tmp_path / "candidate_2"
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=ledger_path,
        expected_ledger_sha256=ledger_sha256,
        evaluation_metrics=release_case["evaluation"],
        destination=destination_2,
    )
    return destination_2


def test_activate_pack_writes_valid_pointer(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    pointer_path = tmp_path / "active_pack.json"
    pointer = pack_activation.activate_pack(release_case["destination"], pointer_path)
    assert pointer["schema"] == pack_activation.ACTIVE_POINTER_SCHEMA
    assert pointer["last_known_good"] is None
    assert pointer_path.is_file()


def test_activate_pack_rejects_non_candidate_state(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    manifest_path = release_case["destination"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "quarantined"
    unsigned = {k: v for k, v in manifest.items() if k != "bundle_id"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    manifest["bundle_id"] = hashlib.sha256(canonical).hexdigest()
    manifest_path.chmod(0o644)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    sidecar = release_case["destination"] / "manifest.json.sha256"
    sidecar.chmod(0o644)
    sidecar.write_text(hashlib.sha256(manifest_path.read_bytes()).hexdigest() + "\n", encoding="ascii")
    with pytest.raises(pack_activation.PackActivationError, match="quarantined"):
        pack_activation.activate_pack(release_case["destination"], tmp_path / "active_pack.json")


def test_validate_active_pack_detects_mutation(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    pointer_path = tmp_path / "active_pack.json"
    pack_activation.activate_pack(release_case["destination"], pointer_path)
    assert pack_activation.validate_active_pack(pointer_path)["active"]["bundle_id"]

    # Mutate an artifact after activation -- must fail closed.
    tampered = release_case["destination"] / "dict_a.jsonl"
    tampered.chmod(0o644)
    tampered.write_bytes(b'{"tampered":true}\n')
    with pytest.raises(pack_activation.PackActivationError):
        pack_activation.validate_active_pack(pointer_path)


def test_validate_active_pack_missing_pointer_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(pack_activation.PackActivationError, match="no active pack pointer"):
        pack_activation.validate_active_pack(tmp_path / "nope.json")


def test_rollback_restores_prior_active_bundle(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    pointer_path = tmp_path / "active_pack.json"
    first = pack_activation.activate_pack(release_case["destination"], pointer_path)

    second_bundle_dir = _second_bundle(release_case, monkeypatch, tmp_path)
    second = pack_activation.activate_pack(second_bundle_dir, pointer_path)
    assert second["active"]["bundle_id"] != first["active"]["bundle_id"]
    assert second["last_known_good"]["bundle_id"] == first["active"]["bundle_id"]

    rolled_back = pack_activation.rollback_to_last_known_good(pointer_path)
    assert rolled_back["active"]["bundle_id"] == first["active"]["bundle_id"]
    assert rolled_back["last_known_good"] is None

    # Confirm output hashes/metadata truly returned to the prior state (CORE-D2-098).
    validated = pack_activation.validate_active_pack(pointer_path)
    assert validated["active"]["bundle_id"] == first["active"]["bundle_id"]
    assert validated["active"]["manifest_sha256"] == first["active"]["manifest_sha256"]


def test_rollback_without_last_known_good_fails_closed(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    pointer_path = tmp_path / "active_pack.json"
    pack_activation.activate_pack(release_case["destination"], pointer_path)
    with pytest.raises(pack_activation.PackActivationError, match="no last-known-good"):
        pack_activation.rollback_to_last_known_good(pointer_path)


def test_post_activation_smoke_reports_metadata(
    release_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(release_freeze, "_git_snapshot", lambda: release_case["git"])
    release_freeze.freeze_core_candidate(
        producer_dir=release_case["producer"],
        generation_ledger=release_case["ledger"],
        expected_ledger_sha256=release_case["ledger_sha256"],
        evaluation_metrics=release_case["evaluation"],
        destination=release_case["destination"],
    )
    pointer_path = tmp_path / "active_pack.json"
    activated = pack_activation.activate_pack(release_case["destination"], pointer_path)
    smoke = pack_activation.post_activation_smoke(pointer_path, fixed_input_count=5)
    assert smoke["pointer_valid"] is True
    assert smoke["active_bundle_id"] == activated["active"]["bundle_id"]
    assert smoke["fixed_inputs_checked"] == 5
