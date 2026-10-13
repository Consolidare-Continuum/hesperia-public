# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 7 — Error surface from evaluation + optional labeled expectations."""

from __future__ import annotations

from typing import Any


def extract_errors(
    evaluation: dict[str, Any],
    texts: list[str],
    *,
    expected_concepts: list[list[str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build ``dict_errors.jsonl`` rows: unmapped (high estimated gap), wrong_concept (vs expected).
    """
    rows: list[dict[str, Any]] = []
    per = list(evaluation.get("per_text") or [])

    for i, pt in enumerate(per):
        um = float(pt.get("unmapped_lexical_ratio_est") or 0)
        if um > 0.35 and i < len(texts):
            rows.append(
                {
                    "type": "unmapped",
                    "text": texts[i][:2000],
                    "unmapped_ratio_est": round(um, 4),
                }
            )

        if expected_concepts and i < len(expected_concepts):
            exp = set(expected_concepts[i])
            got = set((pt.get("concept_weights") or {}).keys())
            for e in exp:
                if e not in got:
                    rows.append(
                        {
                            "type": "wrong_concept",
                            "text": texts[i][:500],
                            "lexical": "",
                            "expected": e,
                            "actual": "",
                            "detail": "missing_expected",
                        }
                    )

    return rows
