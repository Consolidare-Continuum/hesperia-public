# HESPERIA — pytest session hooks (repo import hygiene).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Repo root: tests/conftest.py -> parent.parent
_REPO = Path(__file__).resolve().parent.parent
_rp = str(_REPO)


def _ensure_repo_runtime_importable() -> None:
    """
    Guarantee top-level `runtime` resolves to this repository.

    Pytest may leave `''` (cwd) ahead of the repo on sys.path; long sessions or
    subprocess helpers can change cwd. A foreign or partial `runtime` in
    sys.modules then shadows the real package → ModuleNotFoundError for
    runtime.pipeline / runtime.services.
    """
    if _rp in sys.path:
        sys.path.remove(_rp)
    sys.path.insert(0, _rp)
    mod = sys.modules.get("runtime")
    if mod is None:
        return
    mf = getattr(mod, "__file__", None) or ""
    if not str(mf).startswith(_rp):
        del sys.modules["runtime"]
        for key in list(sys.modules):
            if key == "runtime" or key.startswith("runtime."):
                del sys.modules[key]


_ensure_repo_runtime_importable()


@pytest.hookimpl(trylast=True)
def pytest_configure(config) -> None:  # noqa: ARG001
    # Run after built-in plugins (e.g. pythonpath) adjust sys.path.
    _ensure_repo_runtime_importable()
    # Legacy sphere.pipeline.run_pipeline remains available for unit tests only.
    os.environ["HESPERIA_SPHERE_PIPELINE_DEV"] = "1"
    # Legacy semantic_field_v1 stub matrices (build_default_matrices) for equation unit tests only.
    os.environ["HESPERIA_SEMANTIC_FIELD_STUB_MATRICES"] = "1"
    # Uniform hex injection (family_source_to_hex_uniform / concept_family_weights_to_hex_source) for legacy hex tests only.
    os.environ["HESPERIA_PCH_UNIFORM_INJECTION_DEV"] = "1"


def pytest_runtest_setup(item) -> None:  # noqa: ARG001
    _ensure_repo_runtime_importable()
