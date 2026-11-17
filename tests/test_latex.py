"""Tests for `lib.latex`."""

import pytest

from lib.latex import float_to_latex_str


@pytest.mark.parametrize(
    "f, latex",
    [
        (2.5, "2.5"),
        (1e-5, "10^{-5}"),
        (2.5e20, "2.5\\times10^{20}"),
    ],
)
def test_float_to_latex_str(f, latex):
    assert float_to_latex_str(f) == latex
