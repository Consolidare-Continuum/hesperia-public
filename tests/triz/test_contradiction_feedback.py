from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_risky_token_ranking_low_conflict() -> None:
    from hesperia.extensions.triz.contradiction_feedback import score_lexical_calibration_risk

    lexical = {
        "span_resolutions": [
            {"winning_concept_id": "T_BAD"},
            {"winning_concept_id": "T_BAD"},
            {"winning_concept_id": "T_OK"},
        ]
    }
    rows = [
        {"pair": ["T_BAD", "X"], "raw_contradiction_score": 0.8, "effective_score": 0.2, "confidence": 0.2},
        {"pair": ["T_OK", "Y"], "raw_contradiction_score": 0.4, "effective_score": 0.35, "confidence": 0.9},
    ]
    unc = {"fuzzy_link_ratio": 0.5, "ambiguous_concept_share": 0.5}
    out = score_lexical_calibration_risk(lexical, rows, unc, top_k=5)
    assert out
    assert out[0]["token"] == "T_BAD"


def test_risky_concept_ranking_unstable_contradiction() -> None:
    from hesperia.extensions.triz.contradiction_feedback import score_concept_calibration_risk

    rows = [
        {"pair": ["C_BAD", "K1"], "raw_contradiction_score": 0.9},
        {"pair": ["C_BAD", "K2"], "raw_contradiction_score": 0.8},
        {"pair": ["C_OK", "K3"], "raw_contradiction_score": 0.2},
    ]
    unc = {"weak_concept_share": 0.6, "ambiguous_concept_share": 0.5}
    activation = {"family_fragmentation_summary": {"global_family_fragmentation": 0.6}}
    out = score_concept_calibration_risk(rows, unc, activation, top_k=5)
    assert out
    assert out[0]["concept"] == "C_BAD"


def test_runtime_vs_calibration_split_differs() -> None:
    from hesperia.extensions.triz.contradiction_feedback import build_contradiction_feedback_signals

    rows_runtime = [{"pair": ["A", "B"], "raw_contradiction_score": 0.8, "effective_score": 0.78, "confidence": 0.92}]
    rows_cal = [{"pair": ["A", "B"], "raw_contradiction_score": 0.8, "effective_score": 0.2, "confidence": 0.2}]
    unc_low = {"lexical_uncertainty": 0.1, "concept_uncertainty": 0.1}
    unc_high = {"lexical_uncertainty": 0.8, "concept_uncertainty": 0.7, "fuzzy_link_ratio": 0.7}
    a = build_contradiction_feedback_signals(contradiction_rows=rows_runtime, uncertainty_package=unc_low)
    b = build_contradiction_feedback_signals(contradiction_rows=rows_cal, uncertainty_package=unc_high)
    sa = a["global_feedback_summary"]["runtime_vs_calibration_conflict_split"]
    sb = b["global_feedback_summary"]["runtime_vs_calibration_conflict_split"]
    assert sa["likely_calibration_pathology"] < sb["likely_calibration_pathology"]


def test_dict_calibration_export_feedback_mode(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "dict_a_engine.jsonl").write_text("", encoding="utf-8")
    (work / "contradiction_package.json").write_text(
        json.dumps({"top_risky_pairs": [{"pair": ["A", "B"], "raw_conflict": 0.7, "effective_conflict": 0.2, "pair_recurrence": 0.8}]}),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        str(_REPO / "tools" / "dict_calibration" / "run_pipeline.py"),
        "eval",
        "--workdir",
        str(work),
        "--emit-contradiction-feedback",
        "--feedback-top-k",
        "5",
    ]
    # no corpus/texts needed, eval has default text
    subprocess.run(cmd, check=True, cwd=_REPO)
    assert (work / "contradiction_feedback_report.json").is_file()
    assert (work / "risky_lexical_items.json").is_file()
    assert (work / "risky_concepts.json").is_file()
    assert (work / "risky_concept_pairs.json").is_file()
