# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / "tools/check_core_calibration_boundary.py"


@pytest.fixture()
def clean_repo(tmp_path: Path) -> Path:
    default = tmp_path / "hesperia/modules/default"
    default.mkdir(parents=True)
    (default / "__init__.py").write_text(
        '"""Clean Class A default module package."""\n',
        encoding="utf-8",
    )
    (default / "matcher.py").write_text(
        "CORE_MATCHER_VERSION = 'v1'\n",
        encoding="utf-8",
    )
    return tmp_path


def _run_checker(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--repo-root",
            str(repo_root),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_core_calibration_boundary_cli_passes_clean_default_package(
    clean_repo: Path,
) -> None:
    result = _run_checker(clean_repo)

    assert result.returncode == 0, result.stderr
    assert "pass" in (result.stdout + result.stderr).casefold() or "ok" in (
        result.stdout + result.stderr
    ).casefold()


@pytest.mark.parametrize(
    "source",
    [
        "from hesperia.modules.tfp import resolver\n",
        "from hesperia.modules import tfp\n",
        "from .. import tfp\n",
        "import hesperia.modules.tfp.private_prompt\n",
        'FIELD_REFERENCE = "hesperia.modules.tfp.private_prompt"\n',
        'importlib.import_module("hesperia.modules." + "tfp")\n',
        'CALIBRATION_DOMAIN = "tfp"\n',
    ],
    ids=[
        "from-import",
        "from-parent-import",
        "relative-parent-import",
        "import",
        "string-reference",
        "dynamic-import",
        "domain-marker",
    ],
)
def test_core_calibration_boundary_cli_rejects_tfp_python_references(
    clean_repo: Path,
    source: str,
) -> None:
    target = clean_repo / "hesperia/modules/default/runtime.py"
    target.write_text(source, encoding="utf-8")

    result = _run_checker(clean_repo)

    assert result.returncode == 1
    assert "tfp" in (result.stdout + result.stderr).casefold()
    assert "runtime.py" in (result.stdout + result.stderr)


def test_core_calibration_boundary_cli_rejects_symlink_directory(
    clean_repo: Path,
    tmp_path: Path,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    (external / "runtime.py").write_text("TFP = True\n", encoding="utf-8")
    target = clean_repo / "hesperia/modules/default/adapter"
    target.symlink_to(external, target_is_directory=True)

    result = _run_checker(clean_repo)

    assert result.returncode == 1
    assert "symlink" in (result.stdout + result.stderr).casefold()


def test_core_calibration_boundary_cli_rejects_malformed_python(
    clean_repo: Path,
) -> None:
    target = clean_repo / "hesperia/modules/default/runtime.py"
    target.write_text("from hesperia.modules import (\n", encoding="utf-8")

    result = _run_checker(clean_repo)

    assert result.returncode == 1
    assert "runtime.py" in (result.stdout + result.stderr)


@pytest.mark.parametrize(
    "relative_path",
    [
        "hesperia/modules/default/tfp_adapter.py",
        "hesperia/modules/default/cache/tfp/private.json",
    ],
    ids=["filename", "directory-name"],
)
def test_core_calibration_boundary_cli_rejects_tfp_path_names(
    clean_repo: Path,
    relative_path: str,
) -> None:
    target = clean_repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}\n", encoding="utf-8")

    result = _run_checker(clean_repo)

    assert result.returncode == 1
    assert "tfp" in (result.stdout + result.stderr).casefold()
    assert Path(relative_path).name in (result.stdout + result.stderr)
