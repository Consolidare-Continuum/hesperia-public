#!/usr/bin/env python3
"""COBALT eval harness — generalizes the G3 pilot (10 queries) to the 50-200 pair scale
fpf_bridge_v7_4_cobalt_corpus_scaleup.md §5 requires.

Pure, injectable-retriever design: `run_eval` takes a `retrieve_fn(query) -> hit` callable, so it
is fully unit-testable against synthetic hits (no live CHROMA-2 needed) and reusable unchanged once
Colombo has the real 50-200 Q->doc pairs and points it at runtime.cobalt.retrieve.compose_and_retrieve.

Does not select which queries belong in the real eval set — that's Colombo's clinical judgment
(v7.4 §5), not something this harness invents. Ships with the G3 pilot's own 10 queries as a
documented starting seed, same discipline as the branch-facet classifier's seed terms.

Ref: fpf_bridge_v7_4_cobalt_corpus_scaleup.md §5, §8. Precedent: COLOMBO-COBALT-05-G3-EVAL.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# The G3 pilot's own 10 queries (COLOMBO-COBALT-05-G3-EVAL-2026-06-29.md), preserved verbatim as
# the documented seed for expansion — not discarded, per v7.4 §5 ("use the G3 pilot's 10 as a
# seed, expand with Colombo's clinical judgment").
G3_PILOT_SEED: tuple[tuple[str, bool], ...] = (
    ("TFP transference clinical", True),
    ("borderline Kernberg", True),
    ("countertransference", True),
    ("Doering erotic transference", True),
    ("mood regulation anxiety", True),
    ("personality disorder psychodynamic", True),
    ("Meltzer psychoanalysis", True),
    ("narcissistic transference TFP", True),
    ("TCP IP networking (control)", False),
    ("quantum Aaronson (control)", False),
)


@dataclass
class EvalQuery:
    query: str
    expected_clinical: bool
    label: str = ""


@dataclass
class EvalResult:
    query: str
    expected_clinical: bool
    hit_doc_name: str
    is_clinical_hit: bool
    correct: bool


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)
    total: int = 0
    correct: int = 0

    @property
    def pass_rate(self) -> float:
        return (self.correct / self.total) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "correct": self.correct,
            "pass_rate": round(self.pass_rate, 4),
            "results": [
                {
                    "query": r.query,
                    "expected_clinical": r.expected_clinical,
                    "hit_doc_name": r.hit_doc_name,
                    "is_clinical_hit": r.is_clinical_hit,
                    "correct": r.correct,
                }
                for r in self.results
            ],
        }


def seed_queries() -> list[EvalQuery]:
    """The G3 pilot's 10 queries, as EvalQuery objects — a starting point, not the target
    50-200 set. Colombo expands this (v7.4 §5); this function just preserves what already exists."""
    return [EvalQuery(query=q, expected_clinical=exp) for q, exp in G3_PILOT_SEED]


def _default_clinical_check(doc_name: str) -> bool:
    """Same substring convention the G3 pilot report and COBALT-19's gold test already use."""
    return "tfp" in (doc_name or "").lower() or "kernberg" in (doc_name or "").lower()


def run_eval(
    queries: list[EvalQuery],
    retrieve_fn: Callable[[str], dict],
    *,
    clinical_check: Callable[[str], bool] = _default_clinical_check,
) -> EvalReport:
    """Run each query through `retrieve_fn`, check the top hit's doc_name against
    `clinical_check`, and score against `expected_clinical`. `retrieve_fn` returning a
    `compose_and_retrieve`-shaped packet (dict with `hits: [...]`) is the expected real-world
    shape; tests pass a synthetic stand-in."""
    report = EvalReport()
    for eq in queries:
        packet = retrieve_fn(eq.query)
        hits = packet.get("hits") or []
        top_name = str(hits[0].get("doc_name", "")) if hits else ""
        is_clinical = clinical_check(top_name)
        correct = is_clinical == eq.expected_clinical
        report.results.append(EvalResult(
            query=eq.query,
            expected_clinical=eq.expected_clinical,
            hit_doc_name=top_name,
            is_clinical_hit=is_clinical,
            correct=correct,
        ))
        report.total += 1
        if correct:
            report.correct += 1
    return report


def write_report(report: EvalReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
