from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tools.dict_calibration.clearance_resume import run_post
from tools.dict_calibration.env_defaults import assert_domain_corpus_pairing
from tools.dict_calibration.run_pipeline import (
    _default_engine_paths,
    cmd_eval,
    cmd_propose,
    cmd_run_all,
)
from tools.dict_calibration.propose_llm import _templates_for


def test_domain_pairing_rejects_unclassified_corpus() -> None:
    with pytest.raises(ValueError, match="must be under"):
        assert_domain_corpus_pairing("core", "/tmp/unclassified-corpus")


def test_default_engine_paths_rejects_unknown_domain(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="domain must be"):
        _default_engine_paths(tmp_path, domain="typo")


def test_propose_template_rejects_unknown_domain() -> None:
    with pytest.raises(ValueError, match="domain must be"):
        _templates_for("typo")  # type: ignore[arg-type]


def test_post_rejects_domain_that_differs_from_propose_checkpoint(
    tmp_path: Path,
) -> None:
    clearance = tmp_path / ".clearance"
    clearance.mkdir()
    (clearance / "propose_state.json").write_text(
        json.dumps({"domain": "core"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="propose_state domain='core'.*domain='tfp'"):
        run_post(tmp_path, corpus=tmp_path / "hesperia/modules/tfp/corpus", domain="tfp")


def test_direct_eval_rejects_cross_domain_corpus(tmp_path: Path) -> None:
    args = argparse.Namespace(
        workdir=str(tmp_path),
        corpus=str(tmp_path / "hesperia/modules/tfp/corpus"),
        texts_file=None,
        dict_b=None,
        domain="core",
        eval_max_files=0,
        eval_max_chars=0,
    )

    with pytest.raises(ValueError, match="domain=core forbids TFP"):
        cmd_eval(args)


def test_direct_propose_rejects_cross_domain_catalog(tmp_path: Path) -> None:
    args = argparse.Namespace(
        workdir=str(tmp_path),
        dict_b=[str(tmp_path / "dict_b_tfp.jsonl")],
        domain="core",
        max_concepts=10,
        propose_batch_size=2,
        catalog_limit=10,
        limit=0,
        dry_run=True,
    )

    with pytest.raises(ValueError, match="domain=core forbids TFP dict_b"):
        cmd_propose(args)


def test_generic_catalog_name_cannot_hide_opposite_lane(tmp_path: Path) -> None:
    tfp_catalog = tmp_path / "hesperia/modules/tfp/catalog/dict_b.jsonl"

    with pytest.raises(ValueError, match="domain=core forbids TFP dict_b"):
        assert_domain_corpus_pairing("core", None, dict_b_paths=[tfp_catalog])


def test_run_all_rejects_cross_domain_corpus_before_pipeline_bytes(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        budget=False,
        corpus=str(tmp_path / "hesperia/modules/tfp/corpus"),
        workdir=str(tmp_path / "output"),
        domain="core",
    )

    with pytest.raises(ValueError, match="domain=core forbids TFP"):
        cmd_run_all(args)
    assert not Path(args.workdir).exists()
