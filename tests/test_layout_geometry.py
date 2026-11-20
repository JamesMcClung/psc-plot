import pytest

from lib.plotting.layout.geometry import Box, Margins, even_figure_size, sizes_close


def test_box_edges():
    box = Box(1.0, 2.0, 3.0, 4.0)
    assert (box.x1, box.y1) == (4.0, 6.0)


def test_box_to_figure_fraction():
    assert Box(1.0, 2.0, 3.0, 4.0).to_figure_fraction(10.0, 8.0) == pytest.approx((0.1, 0.25, 0.3, 0.5))


def test_margins_max():
    assert Margins(1, 0, 2, 0).max(Margins(0, 3, 1, 4)) == Margins(1, 3, 2, 4)


def test_sizes_close():
    assert sizes_close(1.0, 1.0 + 1e-12, 100)
    assert not sizes_close(1.0, 1.01, 100)


def test_even_figure_size():
    assert even_figure_size(4.005, 3.0, 100) == pytest.approx((4.02, 3.0))
