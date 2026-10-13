# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Deterministic sequence operations: trajectory build and compress.
Pure numerical/sequence operations; no pipeline logic.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def build_trajectory(area_sequence: list[int] | np.ndarray) -> list[int]:
    """
    Return the full ordered path of areas as a list.
    Deterministic: same input always yields same output.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    return arr.tolist()


def compress_trajectory(
    area_sequence: list[int] | np.ndarray,
    *,
    segment_form: bool = False,
) -> list[int] | list[dict[str, Any]]:
    """
    Collapse consecutive identical areas into a sequence of distinct areas
    (or into segment form with area and length).

    If segment_form is False: returns list of area ids, e.g. [2, 5, 4, 1].
    If segment_form is True: returns list of {"area": int, "length": int}.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    if arr.size == 0:
        return [] if not segment_form else []

    # Consecutive runs: indices where value changes (or start)
    changes = np.concatenate([[True], arr[1:] != arr[:-1]])
    areas = arr[changes]
    if not segment_form:
        return areas.tolist()

    # Segment form: (area, length) for each run
    run_starts = np.where(changes)[0]
    lengths = np.diff(np.concatenate([run_starts, [len(arr)]]))
    return [
        {"area": int(a), "length": int(ln)}
        for a, ln in zip(areas.tolist(), lengths.tolist(), strict=True)
    ]
