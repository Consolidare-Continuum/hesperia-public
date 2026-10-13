"""Engine Dynamics version alignment (VERSION.yaml authority)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml


def _expected_version() -> str:
    root = Path(__file__).resolve().parents[1]
    doc = yaml.safe_load((root / "VERSION.yaml").read_text(encoding="utf-8"))
    return str(doc.get("system_version"))


def test_version_yaml_system_version():
    root = Path(__file__).resolve().parents[1]
    doc = yaml.safe_load((root / "VERSION.yaml").read_text(encoding="utf-8"))
    assert doc.get("system_version") == _expected_version()
    assert doc.get("schema", {}).get("public_output") == "v1"


def test_hesperia_version_matches_release():
    import hesperia

    assert hesperia.__version__ == _expected_version()


def test_release_meta():
    from hesperia.engine import release_meta

    assert release_meta.ENGINE_DYNAMICS_VERSION == _expected_version()
    assert "Engine Dynamics" in release_meta.PRODUCT_LINE


def test_pyproject_version():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "pyproject.toml must declare [project].version"
    assert m.group(1) == _expected_version()
