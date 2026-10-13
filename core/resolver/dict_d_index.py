# HESPERIA — RAD. Dict D (concept x concept co-occurrence) index for the resolver (CHI-015 O4).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Minimal, dependency-free Dict D loader for ``core/resolver``.

Deliberately does not import ``tools/dict_calibration`` (build-time, OpenAI-coupled
package) into this runtime/sealed layer — see ``tools/dict_calibration/__init__.py``.
Row shape/validation duplicated minimally here rather than shared, on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED = ("concept_id_a", "concept_id_b", "npmi")


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def load_dict_d_pairs(path: Path | str) -> dict[tuple[str, str], float]:
    """
    Read a ``dict_d_*.jsonl`` file into ``{(concept_id_a, concept_id_b): npmi}``,
    keys canonically sorted so lookup order doesn't matter. Skips rows missing a
    required field rather than raising — this is a runtime lookup table, not a
    calibration-time validator (that's ``tools/dict_calibration/dict_d_io.py``).
    """
    out: dict[tuple[str, str], float] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row: dict[str, Any] = json.loads(line)
        if not all(k in row for k in REQUIRED):
            continue
        a, b = str(row["concept_id_a"]), str(row["concept_id_b"])
        try:
            npmi = float(row["npmi"])
        except (TypeError, ValueError):
            continue
        out[_pair_key(a, b)] = npmi
    return out
