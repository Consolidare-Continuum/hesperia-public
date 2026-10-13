# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CORE-D2 W9 — atomic pack activation, startup validation, rollback.

Builds and tests the activation MECHANISM only. No task in this module is
ever called against the real production
``assets/config/engine_constants.json`` weight or a real active-pack
pointer — the actual production activation (a real Dict D bundle from a
clean-generation rerun, a real justified weight per
``ETHAN-CORE-D2-W9-ACTIVATION-CRITERIA.md``) is deferred pending
``CORE-D2-049-C/D``, per explicit operator decision 2026-09-16 ("build
everything else first, rerun later").
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .core_candidate import sha256_file
from .evaluate import _read_bundle

ACTIVE_POINTER_SCHEMA = "hesperia.dict_calibration.active_pack_pointer.v1"


class PackActivationError(ValueError):
    """Raised on any fail-closed activation, validation, or rollback violation."""


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    content = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode(
        "utf-8"
    )
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_pointer(active_pointer_path: Path) -> dict[str, Any]:
    if not active_pointer_path.is_file():
        raise PackActivationError(f"no active pack pointer at {active_pointer_path}")
    pointer = json.loads(active_pointer_path.read_text(encoding="utf-8"))
    if pointer.get("schema") != ACTIVE_POINTER_SCHEMA:
        raise PackActivationError("active pack pointer has unexpected schema")
    return pointer


def activate_pack(candidate_bundle_dir: Path, active_pointer_path: Path, *, domain: str = "core") -> dict[str, Any]:
    """Atomically point ``active_pointer_path`` at ``candidate_bundle_dir`` (CORE-D2-091/093).

    Validates the candidate bundle strictly first via the same
    ``_read_bundle`` logic W2/W3 already use — no separate, weaker
    activation-time validator. Only ``candidate``/``release_candidate``
    states may be activated (CORE-D2-092's "prohibit implicit... activation"
    reads as: activation is only ever this explicit call, never a side
    effect of any other operation). Whatever was previously active is
    carried forward as ``last_known_good`` inside the same pointer file —
    no separate last-known-good file to go stale or drift out of sync.
    """
    try:
        bundle = _read_bundle(candidate_bundle_dir, require_manifest_v2=True)
    except ValueError as exc:
        raise PackActivationError(f"candidate bundle failed validation: {exc}") from exc
    manifest_path = candidate_bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("state") not in {"candidate", "release_candidate"}:
        raise PackActivationError(f"cannot activate from state {manifest.get('state')!r}")

    previous: dict[str, Any] | None = None
    if active_pointer_path.exists():
        existing = _read_pointer(active_pointer_path)
        previous = existing.get("active")

    new_pointer = {
        "schema": ACTIVE_POINTER_SCHEMA,
        "domain": domain,
        "active": {
            "bundle_dir": str(candidate_bundle_dir.resolve()),
            "bundle_id": bundle["bundle_id"],
            "manifest_sha256": sha256_file(manifest_path),
        },
        "last_known_good": previous,
    }
    _atomic_write_json(active_pointer_path, new_pointer)
    return new_pointer


def validate_active_pack(active_pointer_path: Path) -> dict[str, Any]:
    """Startup validation (CORE-D2-094): re-validates the currently pointed-at
    bundle from scratch. Fails closed on a missing directory, a mutated
    manifest (hash mismatch), or any artifact/schema violation
    ``_read_bundle`` itself would reject — never silently accepts a
    mismatched or partially-missing pack."""
    pointer = _read_pointer(active_pointer_path)
    active = pointer.get("active")
    if not isinstance(active, dict):
        raise PackActivationError("active pack pointer missing 'active' block")
    bundle_dir = Path(active["bundle_dir"])
    if not bundle_dir.is_dir():
        raise PackActivationError(f"active bundle directory missing: {bundle_dir}")
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file() or sha256_file(manifest_path) != active.get("manifest_sha256"):
        raise PackActivationError("active manifest hash mismatch — bundle mutated since activation")
    try:
        bundle = _read_bundle(bundle_dir, require_manifest_v2=True)
    except ValueError as exc:
        raise PackActivationError(f"active bundle failed re-validation: {exc}") from exc
    if bundle["bundle_id"] != active.get("bundle_id"):
        raise PackActivationError("active bundle_id mismatch")
    return pointer


def rollback_to_last_known_good(active_pointer_path: Path) -> dict[str, Any]:
    """One-command rollback (CORE-D2-096): swap ``active`` for ``last_known_good``.

    One level of history only, by design — the pointer that results from a
    rollback carries no further ``last_known_good`` of its own, so a second
    consecutive rollback fails closed rather than silently going further
    back than anyone asked for.
    """
    pointer = _read_pointer(active_pointer_path)
    lkg = pointer.get("last_known_good")
    if lkg is None:
        raise PackActivationError("no last-known-good to roll back to")
    rolled_back = {
        "schema": ACTIVE_POINTER_SCHEMA,
        "domain": pointer["domain"],
        "active": lkg,
        "last_known_good": None,
    }
    _atomic_write_json(active_pointer_path, rolled_back)
    return rolled_back


def post_activation_smoke(active_pointer_path: Path, *, fixed_input_count: int) -> dict[str, Any]:
    """Fixed-input post-activation smoke (CORE-D2-095): re-validates the pack
    and reports activation metadata. Does not itself run the engine over the
    fixed inputs — callers run those separately and compare against this
    call's ``active_bundle_id`` for provenance binding."""
    pointer = validate_active_pack(active_pointer_path)
    return {
        "pointer_valid": True,
        "active_bundle_id": pointer["active"]["bundle_id"],
        "domain": pointer["domain"],
        "fixed_inputs_checked": fixed_input_count,
    }
