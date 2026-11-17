"""Tests for `PlotInfo`'s labels."""

import numpy as np
import pytest

from lib.latex import Latex
from lib.plotting.plot_info import LineInfo


@pytest.mark.parametrize(
    "value, label",
    [
        (0.0, "a = 0.000"),
        (0.3314562, "a = 0.331"),
        (2e-5, "a = 2\\times10^{-5}"),
        (-1.23456e7, "a = -1.235\\times10^{7}"),
    ],
)
def test_coord_label(value, label):
    """Fixed-point at ordinary magnitudes (e.g. times), a power of 10 where that would hide the value (e.g. a small fitted coefficient)."""
    info = LineInfo(x_dim="y", y_dim="f", x_data=np.zeros(1), y_data=np.zeros(1), dim_displays={"a": Latex("a")}, scalar_coord_values={"a": value})
    assert info.get_coord_label("a") == Latex(label)
