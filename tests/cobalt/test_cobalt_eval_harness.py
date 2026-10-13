# tests/cobalt/test_cobalt_eval_harness.py — fpf_bridge_v7_4 §5 eval harness.
from __future__ import annotations

from tools.cobalt_eval_harness import EvalQuery, run_eval, seed_queries, G3_PILOT_SEED


def _fake_retrieve_all_clinical(query: str) -> dict:
    return {"hits": [{"doc_name": "RU - Kernberg - TFP clinical guide.md"}]}


def _fake_retrieve_all_noise(query: str) -> dict:
    return {"hits": [{"doc_name": "networking-iot-architecture.pdf"}]}


def test_seed_queries_preserves_g3_pilot_set():
    seeds = seed_queries()
    assert len(seeds) == len(G3_PILOT_SEED) == 10
    assert seeds[0].query == "TFP transference clinical"
    assert seeds[0].expected_clinical is True
    assert seeds[-1].expected_clinical is False


def test_run_eval_scores_correctly_against_all_clinical_retriever():
    queries = seed_queries()
    report = run_eval(queries, _fake_retrieve_all_clinical)
    assert report.total == 10
    # 8 of 10 seed queries expect a clinical hit; a retriever that always returns clinical
    # gets those 8 right and the 2 controls (expect non-clinical) wrong.
    assert report.correct == 8


def test_run_eval_scores_correctly_against_noise_retriever():
    queries = seed_queries()
    report = run_eval(queries, _fake_retrieve_all_noise)
    assert report.correct == 2  # only the 2 controls (expected non-clinical) score right


def test_empty_hits_treated_as_non_clinical_not_a_crash():
    report = run_eval([EvalQuery("anything", expected_clinical=True)], lambda q: {"hits": []})
    assert report.total == 1
    assert report.correct == 0
    assert report.results[0].hit_doc_name == ""


def test_pass_rate_computed():
    queries = [EvalQuery("q1", True), EvalQuery("q2", True)]
    report = run_eval(queries, _fake_retrieve_all_clinical)
    assert report.pass_rate == 1.0
