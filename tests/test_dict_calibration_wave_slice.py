# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from tools.dict_calibration.run_pipeline import _wave_slice_rows


def test_wave_slice_partitions() -> None:
    rows = [{"i": i} for i in range(10)]
    a = _wave_slice_rows(rows, 1, 2)
    b = _wave_slice_rows(rows, 2, 2)
    assert len(a) == 5 and len(b) == 5
    assert a[0]["i"] == 0 and b[0]["i"] == 5


def test_wave_slice_noop_without_index() -> None:
    rows = [{"i": 0}]
    assert _wave_slice_rows(rows, None, 3) == rows
