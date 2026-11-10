"""Tests for `--log` and `--exp`."""

import numpy as np
import pandas as pd
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.exp import Exp
from lib.data.adaptors.log import Log
from lib.data.loader import load
from lib.parsing.parse import parse_steps


def _positive_hx():
    """hx_fc, shifted to be strictly positive."""
    pfd = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    return pfd.with_active(data=abs(pfd["hx_fc"]) + 1)


def test_log_natural_field():
    data = _positive_hx()
    out = Log(None).apply(data)
    xr.testing.assert_allclose(out["hx_fc"], np.log(data["hx_fc"]))
    assert out.active_info.display.latex == f"\\ln({data.active_info.display.latex})"


def test_log_keeps_unit_and_scale():
    data = _positive_hx()
    out = Log(None).apply(data)
    assert out.active_info.unit == data.active_info.unit
    assert out.active_info.scale == data.active_info.scale


def test_log_base_10():
    data = _positive_hx()
    out = Log(10.0).apply(data)
    xr.testing.assert_allclose(out["hx_fc"], np.log10(data["hx_fc"]))
    assert out.active_info.display.latex == f"\\log_{{10.0}}({data.active_info.display.latex})"


def test_log_list():
    prt = load(CONFIG_2D, "prt.e").with_active(key="w")
    out = Log(None).apply(prt).data["w"].compute()
    pd.testing.assert_series_equal(out, np.log(prt.data["w"].compute()))


def test_log_parse():
    [natural] = parse_steps(["--log"])
    assert isinstance(natural, Log) and natural.base is None
    [base2] = parse_steps(["--log 2"])
    assert isinstance(base2, Log) and base2.base == 2.0


def test_exp_field():
    data = _positive_hx()
    out = Exp().apply(data)
    xr.testing.assert_allclose(out["hx_fc"], np.exp(data["hx_fc"]))
    assert out.active_info.display.latex == f"\\exp({data.active_info.display.latex})"
    assert out.active_info.unit == data.active_info.unit
    assert out.active_info.scale == data.active_info.scale


def test_log_exp_round_trip():
    data = _positive_hx()
    out = Exp().apply(Log(None).apply(data))
    xr.testing.assert_allclose(out["hx_fc"], data["hx_fc"])
    assert out.active_info.unit == data.active_info.unit
    assert out.active_info.scale == data.active_info.scale


def test_exp_parse():
    [adaptor] = parse_steps(["--exp"])
    assert isinstance(adaptor, Exp)
