# HESPERIA — Semantic / shape contract for shipped structural JSON (drift resistance).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.public_output_contract import assert_canonical_structural_json_contract

# Contrasting inputs: degenerate vs rich — catches normalization / scaling regressions.
_LOW_SIGNAL = "test"
_STRUCTURED_SIGNAL = (
    "Systematic planning improves long-term stability and reduces uncertainty."
)


def _assets() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "lexicon" / "curated"


@pytest.mark.skipif(not _assets().is_dir(), reason="lexicon/curated missing")
@pytest.mark.parametrize(
    "text",
    [
        _LOW_SIGNAL,
        _STRUCTURED_SIGNAL,
        "justice fairness order harm conflict trust",
        "aaaa",
        " ",
    ],
)
def test_structural_output_semantic_contract(text: str) -> None:
    from runtime.services.analysis_service import run_structural_analysis

    out = run_structural_analysis(
        text,
        assets_root=_assets(),
        stages="full",
        attach_version=True,
    )
    assert_canonical_structural_json_contract(out)
