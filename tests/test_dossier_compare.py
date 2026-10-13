# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dossier comparison tests.
Verify identical → no diff, anomaly delta, policy change, stable family difference.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from runtime.dossier.compare_dossiers import compare_dossiers


def _dossier(
    engine_version: str = "1.0.0",
    policy_mode: str = "STRUCTURE_PLUS_CONTEXT",
    document_anomaly: float = 0.1,
    dominant_area_distribution: dict | None = None,
    stable_family_core: list | None = None,
    mean_confidence: float = 0.85,
) -> dict:
    return {
        "meta": {
            "engine_version": engine_version,
            "run_manifest": {"policy_mode": policy_mode},
        },
        "global_structure": {
            "document_anomaly": document_anomaly,
            "dominant_area_distribution": dominant_area_distribution or {"1": 0.5, "2": 0.5},
            "stable_family_core": stable_family_core or [10, 20],
            "confidence_profile": {"mean_confidence": mean_confidence},
        },
    }


def test_identical_dossiers_no_differences(tmp_path: Path) -> None:
    """Identical dossiers produce no structural differences."""
    d = _dossier()
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text(json.dumps(d), encoding="utf-8")
    fb.write_text(json.dumps(d), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is not None
    assert result["engine_version_changed"] is False
    assert result["policy_changed"] is False
    assert result["document_anomaly_delta"] == 0.0
    assert result["stable_family_difference"] == {"removed": [], "added": []}
    assert result["area_distribution_delta"] == {}
    assert result["mean_confidence_delta"] == 0.0


def test_changed_anomaly_delta_detected(tmp_path: Path) -> None:
    """Changed document_anomaly is reported as delta."""
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text(json.dumps(_dossier(document_anomaly=0.1)), encoding="utf-8")
    fb.write_text(json.dumps(_dossier(document_anomaly=0.22)), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is not None
    assert result["document_anomaly_delta"] == 0.12


def test_changed_policy_detected(tmp_path: Path) -> None:
    """Changed policy_mode is detected."""
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text(json.dumps(_dossier(policy_mode="STRUCTURE_ONLY")), encoding="utf-8")
    fb.write_text(json.dumps(_dossier(policy_mode="FULL_INTERPRETATION")), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is not None
    assert result["policy_changed"] is True


def test_changed_family_core_detected(tmp_path: Path) -> None:
    """Stable family core difference yields removed/added."""
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text(json.dumps(_dossier(stable_family_core=[10, 20, 30])), encoding="utf-8")
    fb.write_text(json.dumps(_dossier(stable_family_core=[10, 40])), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is not None
    sf = result["stable_family_difference"]
    assert set(sf["removed"]) == {20, 30}
    assert set(sf["added"]) == {40}


def test_engine_version_changed(tmp_path: Path) -> None:
    """Engine version change is detected."""
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text(json.dumps(_dossier(engine_version="1.0.0")), encoding="utf-8")
    fb.write_text(json.dumps(_dossier(engine_version="2.0.0")), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is not None
    assert result["engine_version_changed"] is True


def test_missing_file_returns_none(tmp_path: Path) -> None:
    """Missing dossier path yields None."""
    fa = tmp_path / "a.json"
    fb = tmp_path / "nonexistent.json"
    fa.write_text(json.dumps(_dossier()), encoding="utf-8")
    result = compare_dossiers(fa, fb)
    assert result is None
