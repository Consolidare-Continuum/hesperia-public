# HESPERIA — TFP-GATE-INV: ensure enforcement + CD + determinism suites stay wired (see test_tfp_*_enf.py).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations


def test_concept_invariant_enf_suite_importable() -> None:
    import tests.test_tfp_concept_invariants_enf  # noqa: F401
    import tests.test_tfp_cd_delta_enf  # noqa: F401
    import tests.test_tfp_unmapped_gate_enf  # noqa: F401
    import tests.test_tfp_rel_realism_enf  # noqa: F401


def test_concept_invariant_supporting_modules_importable() -> None:
    import tests.concept_dictionary.test_cd_executor  # noqa: F401
    import tests.test_env_determinism  # noqa: F401
