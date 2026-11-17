"""Tests for `--derive`'s expression grammar."""

import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.derive import Derive
from lib.data.adaptors.fit import Fit
from lib.data.data_world import DataWorld
from lib.data.loader import load


def _derive(*expressions: str):
    world = DataWorld({"pfd": load(CONFIG_2D, "pfd")}, "pfd", config=CONFIG_2D)
    for expression in expressions:
        world = Derive(expression).apply_world(world)
    data = world.require_active_data()
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


def test_log_function():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("w=log(hx_fc^2+1)"), np.log(hx**2 + 1))


def test_exp_function():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("w=2*exp(hx_fc)"), 2 * np.exp(hx))


def test_unknown_function():
    with pytest.raises(ValueError, match="unknown function 'sin'"):
        _derive("w=sin(hx_fc)")


def test_dim_coordinate():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("w=hx_fc*y"), hx * hx.y)


def test_bare_coordinate():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("w=2*t"), 2 * hx.t)


def test_scoped_coordinate():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("w=hx_fc*pfd_moments::z"), hx * hx.z)


def test_fit_coefficient():
    """A --fit coefficient is a (non-dim) coord of the curve, so --derive can use it."""
    pfd = load(CONFIG_2D, "pfd")
    world = DataWorld({"pfd": pfd.with_active(key="hx_fc")}, "pfd", config=CONFIG_2D)
    world = Fit(["c"], "f=c*y").apply_world(world)
    data = Derive("w=c*y").apply_world(world).require_active_data()
    xr.testing.assert_allclose(data["w"].broadcast_like(data["f"]).transpose(*data["f"].dims), data["f"])


def test_variable_shadows_coordinate():
    hx = load(CONFIG_2D, "pfd")["hx_fc"]
    xr.testing.assert_allclose(_derive("y=2*hx_fc", "w=y"), 2 * hx)
