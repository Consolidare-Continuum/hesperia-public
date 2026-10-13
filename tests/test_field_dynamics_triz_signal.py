# HESPERIA — RAD. TRIZ → 12-area contradiction drive.

from hesperia.extensions.dynamics.triz_signal import contradiction_signal_12_from_con_rows


def test_contradiction_signal_from_rows_two_areas():
    rows = [
        {"score": 0.8, "area_a": 1, "area_b": 3},
        {"score": 0.5, "area_a": 1, "area_b": 2},
    ]
    sig = contradiction_signal_12_from_con_rows(rows)
    assert len(sig) == 12
    assert sig[1] == 1.0
    assert sig[3] > 0 and sig[2] > 0


def test_contradiction_signal_empty():
    assert contradiction_signal_12_from_con_rows([]) == [0.0] * 12


def test_contradiction_signal_area_cluster_fallback():
    rows = [{"score": 0.4, "area_a": None, "area_b": None, "area_cluster": [0, 5]}]
    sig = contradiction_signal_12_from_con_rows(rows)
    assert sig[0] == 1.0 and sig[5] == 1.0
