# HESPERIA — Cross-plane contradiction package unit tests.

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_build_package_empty_contradictions() -> None:
    from hesperia.extensions.triz.crossplane_contradiction import build_crossplane_contradiction_package
    from hesperia.nlp.session_parser import analyze_session

    act = analyze_session("neutral words only neutral", embedding=None, contradictions=None)
    pkg = build_crossplane_contradiction_package(act, {}, None)
    assert pkg["global_contradiction_load"] == 0.0
    assert pkg["contradiction_coupling_active"] is False
