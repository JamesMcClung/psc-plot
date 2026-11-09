"""Tests for `--derive`'s expression grammar."""

import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.derive import Derive
from lib.data.data_world import DataWorld
from lib.data.loader import load


def _derive(expression: str):
    world = DataWorld({"pfd": load(CONFIG_2D, "pfd")}, "pfd", config=CONFIG_2D)
    data = Derive(expression).apply_world(world).require_active_data()
    return data[data.active_key]


@pytest.mark.parametrize("literal, value", [("1i", 1j), ("2.5i", 2.5j), ("-3i", -3j), ("1e2i", 100j), (".5i", 0.5j)])
def test_imaginary_literal(literal, value):
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive(f"w=hx_fc*{literal}"), hx * value)


def test_complex_combination():
    pfd = load(CONFIG_2D, "pfd")
    xr.testing.assert_allclose(_derive("w=hx_fc+1i*hz_fc"), pfd["hx_fc"] + 1j * pfd["hz_fc"])


def test_bare_i_is_a_variable():
    with pytest.raises(Exception, match="No variable named 'i'"):
        _derive("w=hx_fc*i")


@pytest.mark.parametrize("expression", ["w=1 i", "w=2ix"])
def test_i_must_touch_its_number(expression):
    with pytest.raises(Exception):
        Derive(expression)
