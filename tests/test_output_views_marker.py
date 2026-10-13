"""Register pytest marker `output_views` (T51); Django tests live under output_views/."""

import pytest

pytestmark = pytest.mark.output_views


def test_output_views_marker_registered() -> None:
    assert True
