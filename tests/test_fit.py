"""Tests for `--fit`."""

import numpy as np
import pytest
import scipy.stats
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.fit import Fit
from lib.data.adaptors.log import Log
from lib.data.data_with_attrs import Field, FieldMetadata
from lib.data.data_world import DataWorld
from lib.data.loader import load
from lib.latex import Latex
from lib.scale import LogScale
from lib.var_info import VarInfo

# --- fields ---


def _info(key: str, unit: str = "", **kwargs) -> VarInfo:
    return VarInfo(Latex(key), Latex(unit), key=key, **kwargs)


def _field(da: xr.DataArray, **extra: xr.DataArray) -> Field:
    """A field whose active variable `f` is `da`, with unit U and a log scale."""
    var_infos = {"f": _info("f", "U", scale=LogScale())} | {dim: _info(dim) for dim in da.dims} | {key: _info(key) for key in extra}
    return Field({"f": da} | extra, FieldMetadata(prepath="pfd", active_key="f", var_infos=var_infos))


def _fit(data, names: list[str], assignment: str):
    world = DataWorld({"pfd": data}, "pfd", config=CONFIG_2D)
    return Fit(names, assignment).apply_world(world).require_active_data()


def _f_y_t() -> xr.DataArray:
    """f(y, t) = (t+1) * y on y = 1..5, t = 0..2."""
    y = np.arange(1.0, 6.0)
    t = np.arange(3.0)
    return xr.DataArray(np.outer(y, t + 1), coords={"y": y, "t": t}, dims=("y", "t"))


def test_power_law_matches_linregress():
    """The old hook's log-log linear regression, reproduced by --log + --fit."""
    y = np.linspace(1, 20, 40)
    f = 3 * y**-1.7 * (1 + 0.01 * np.sin(y))
    data = Log(None).apply(_field(xr.DataArray(f, coords={"y": y}, dims="y")))
    curve = _fit(data, ["c", "gamma"], "fit=c-gamma*log(y)")["fit"]

    slope, intercept, *_ = scipy.stats.linregress(np.log(y), np.log(f))
    assert float(curve.coords["gamma"]) == pytest.approx(-slope, rel=1e-6)
    assert float(curve.coords["c"]) == pytest.approx(intercept, rel=1e-6)


def test_field_fit_output_metadata():
    y = np.arange(1.0, 6.0)
    data = _fit(_field(xr.DataArray(2 * y, coords={"y": y}, dims="y")), ["a"], "fit=a*y")
    assert data.active_key == "fit"
    info = data.active_info
    assert info.key == "fit" and not info.display
    assert info.unit == Latex("U") and info.scale == LogScale()
    assert data["fit"].coords["a"].shape == ()
    assert "a" in data.metadata.var_infos
    np.testing.assert_allclose(data["fit"], 2 * y)


def test_field_fit_per_value_dim():
    curve = _fit(_field(_f_y_t()), ["a", "t"], "fit=a*y")["fit"]
    assert curve.coords["a"].dims == ("t",)
    np.testing.assert_allclose(curve.coords["a"], [1, 2, 3])
    assert curve.isel(t=0).coords["a"].shape == ()
    xr.testing.assert_allclose(curve.drop_vars("a"), _f_y_t())


def test_field_fit_two_variables():
    y, z = np.arange(1.0, 5.0), np.arange(1.0, 4.0)
    da = xr.DataArray(2 * y[:, None] + 3 * z[None, :], coords={"y": y, "z": z}, dims=("y", "z"))
    curve = _fit(_field(da), ["a", "b"], "fit=a*y+b*z")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)
    assert float(curve.coords["b"]) == pytest.approx(3.0)
    xr.testing.assert_allclose(curve.drop_vars(["a", "b"]), da)


def test_field_fit_pools_unlisted_dims():
    curve = _fit(_field(_f_y_t()), ["a"], "fit=a*y")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)
    assert set(curve.dims) == {"y", "t"}


def test_field_fit_skips_nans():
    y = np.arange(1.0, 8.0)
    f = 2 * y
    f[[1, 4]] = np.nan
    curve = _fit(_field(xr.DataArray(f, coords={"y": y}, dims="y")), ["a"], "fit=a*y")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_field_fit_named_variable_errors():
    da = _f_y_t()
    with pytest.raises(ValueError, match="--scatter"):
        _fit(_field(da, g=da), ["a"], "fit=a*g")


def test_per_value_name_not_a_dim_errors():
    with pytest.raises(ValueError, match="'q'"):
        _fit(_field(_f_y_t()), ["a", "q"], "fit=a*y")


def test_coefficient_colliding_with_dim_errors():
    with pytest.raises(ValueError, match="'t'"):
        _fit(_field(_f_y_t()), ["t"], "fit=t*y")


def test_expression_without_independent_variable_errors():
    with pytest.raises(ValueError, match="besides the coefficients"):
        Fit(["c"], "fit=c")


def test_no_coefficients_errors():
    with pytest.raises(ValueError, match="coefficient"):
        Fit(["t"], "fit=y")


def test_scoped_variable_errors():
    with pytest.raises(ValueError, match="prepath::key"):
        Fit(["a"], "fit=a*pfd::y")


def test_degenerate_group_errors():
    da = _f_y_t().copy()
    da[1:, 1] = np.nan  # t=1 keeps a single point, fewer than the 2 coefficients
    with pytest.raises(ValueError, match="fewer"):
        _fit(_field(da), ["a", "b", "t"], "fit=a*y+b")


def test_fit_real_field():
    pfd = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    curve = _fit(pfd, ["a", "b", "t"], "fit=a*y+b")["fit"]
    assert set(curve.dims) == set(pfd["hx_fc"].dims)
    assert curve.coords["a"].dims == ("t",)
