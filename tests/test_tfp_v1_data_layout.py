# HESPERIA — TFP-DATA-T15: tfp_v1 skeleton dirs exist (optional in minimal clone).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def tfp_v1() -> Path:
    return REPO / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1"


def test_tfp_v1_expected_directories_when_not_skipped(tfp_v1: Path) -> None:
    if os.environ.get("HESPERIA_SKIP_TFP_V1_LAYOUT_TEST", "").strip().lower() in ("1", "true", "yes", "on"):
        pytest.skip("HESPERIA_SKIP_TFP_V1_LAYOUT_TEST set")
    required = [
        tfp_v1 / "corpus" / "original" / "ru",
        tfp_v1 / "corpus" / "original" / "en",
        tfp_v1 / "corpus" / "sessions",
        tfp_v1 / "dict_a" / "runtime",
        tfp_v1 / "dict_b",
        tfp_v1 / "provenance" / "api" / "runs",
        tfp_v1 / "nlp",
    ]
    missing = [str(p.relative_to(REPO)) for p in required if not p.is_dir()]
    assert not missing, f"missing tfp_v1 dirs: {missing}"
